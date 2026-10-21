---
id: hide-task-window-report
title: 예약 작업 창 숨김 — Builder 보고
date: 2026-10-21
prompt: docs/claude/hide-task-window-builder-prompt.md
authority: order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음 · 예약 작업 생성·변경·실행 없음
---

# 예약 작업 창 숨김 — Builder 보고

## 바뀐 줄 (파일마다 주석 1줄 + `$actionArguments` 맨 앞에 `-WindowStyle Hidden ` 추가)

| 파일 | 줄(수정 뒤) | 바뀐 내용 |
|---|---|---|
| manage-us-stock-strategy/scripts/register_auto_core_task.ps1 | 83(주석), 84 | `'-WindowStyle Hidden -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -RepositoryRoot "{1}" -Command {2}'` |
| manage-us-stock-strategy/scripts/register_host_status_task.ps1 | 79(주석), 80 | `'-WindowStyle Hidden -NoProfile ... -File "{0}" -RepositoryRoot "{1}"'` |
| manage-us-stock-strategy/scripts/register_journal_score_task.ps1 | 80(주석), 81 | 같음 |
| manage-us-stock-strategy/scripts/register_offsite_backup_task.ps1 | 80(주석), 81 | 같음 |
| manage-us-stock-strategy/scripts/register_sec_scheduled_shadow_task.ps1 | 138(주석), 139 | 같음 |
| docs/claude/t2rc-register-task.ps1 | 75(주석), 76 | 같음 |

주석(6개 파일 같은 문장): `# Hidden window: keyboard Ctrl+C in the visible window stopped the decide run on 2026-10-21.`

- 그대로인 것: LogonType Interactive, RunLevel Limited, 트리거 시각·요일, ExecutionTimeLimit, MultipleInstances IgnoreNew, StartWhenAvailable, WakeToRun:$false, 작업 이름, 실행 래퍼 경로, PlanOnly 출력(ACTION은 원래 인자를 찍지 않아 바꾸지 않음, WINDOW_STYLE 줄도 더하지 않음).
- 줄바꿈 CRLF 유지(파일별 CR 줄 수 = 원래 + 1), 비ASCII 문자 0.
- `git diff --stat`: 6 files changed, 12 insertions(+), 6 deletions(-).

## 새 테스트 manage-us-stock-strategy/tests/test_task_window_hidden.py (정적, 스크립트 실행 없음)

1. 6개 파일 각각 `$actionArguments =` 대입이 정확히 1개이고, 따옴표 안 문자열이 `-WindowStyle Hidden -NoProfile -NonInteractive -ExecutionPolicy Bypass -File`로 시작하며, 작업 동작이 `-Argument $actionArguments`를 쓰는지 확인.
2. 6개 파일 모두 `-LogonType Interactive`, `-RunLevel Limited`가 있고 `conhost`가 없는지 확인.
3. 자체 확인: 수정 전 문자열(`'-NoProfile ...`)·`-File` 뒤에 붙인 `-WindowStyle Hidden`·빈 텍스트·대입 2개를 모두 실패로 잡고, 수정 뒤 문자열은 통과시킨다.

## 테스트 결과 (2026-10-21, 이 worktree)

| 패턴 | 결과 |
|---|---|
| test_task_window_hidden.py | 3 OK |
| test_host_status_static.py | 20 OK |
| test_journal_score_task_static.py | 5 OK |
| test_offsite_backup_static.py | 16 OK |
| test_sec_scheduled_shadow.py | 39 OK (skip 1, 기존) |
| test_auto_core*.py | 460 중 실패 1, skip 1 |

auto-core 실패 1건: `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR')` → `['CARD_SECTION_CHANGED', 'CARD_NOT_ACCEPTED_IN_WATCHLIST']`. 이 테스트는 실제 카드 근거 등록부·PLTR 카드·관심목록 파일을 읽는다(test_auto_core_decide.py:1332-1339). 이번 변경은 그 파일들을 건드리지 않았으므로(위 diff 범위) 이번 변경 전부터 있던 실패로 본다. 기준선 실패 여부는 파이프라인 기준선 측정으로 확인한다. 고치지 않음(범위 밖 자료 상태).

## 남은 위험

- `powershell.exe -WindowStyle Hidden`은 콘솔을 먼저 만든 뒤 숨기므로 작업이 시작될 때 창이 잠깐 깜빡일 수 있다. 그 짧은 순간의 키 입력 가능성은 남는다(가장 단순한 한 방식만 쓰라는 지시에 따라 conhost --headless 등은 쓰지 않음).
- 작업이 멈추거나 오래 걸려도 화면에서 보이지 않는다. 확인은 로그(workspace/outputs/auto-core/logs 등의 RUNNER_START/RUNNER_END)와 기존 알림으로만 한다.
- 등록된 작업은 사용자가 다시 등록하기 전까지 예전 인자(창 보임)로 계속 돈다.
- PlanOnly 출력에는 인자가 찍히지 않으므로 숨김 여부는 등록 뒤 작업 정보로 확인한다(아래 3단계).

## 사용자가 병합 뒤 할 일 (관리자 아닌 일반 PowerShell, 저장소 루트에서)

1단계 — 계획만 확인(등록 안 함):

```powershell
.\manage-us-stock-strategy\scripts\register_auto_core_task.ps1 -PlanOnly
.\manage-us-stock-strategy\scripts\register_host_status_task.ps1 -PlanOnly
.\manage-us-stock-strategy\scripts\register_journal_score_task.ps1 -PlanOnly
.\manage-us-stock-strategy\scripts\register_offsite_backup_task.ps1 -PlanOnly
.\manage-us-stock-strategy\scripts\register_sec_scheduled_shadow_task.ps1
.\docs\claude\t2rc-register-task.ps1 -PlanOnly
```

(SEC 스크립트는 인자 없이 실행하면 계획만 출력한다.)

2단계 — 다시 등록(같은 이름 작업을 덮어쓰기만 하고 실행하지 않음):

```powershell
.\manage-us-stock-strategy\scripts\register_auto_core_task.ps1
.\manage-us-stock-strategy\scripts\register_host_status_task.ps1
.\manage-us-stock-strategy\scripts\register_journal_score_task.ps1
.\manage-us-stock-strategy\scripts\register_offsite_backup_task.ps1
.\manage-us-stock-strategy\scripts\register_sec_scheduled_shadow_task.ps1 -Apply
.\docs\claude\t2rc-register-task.ps1
```

t2rc 작업(InvestmentV2-T2rcCheck)과 SEC 작업(GuardedPortfolio-SEC-Shadow-v0.1)은 지금 등록돼 있을 때만 다시 등록한다(등록돼 있지 않으면 새로 만들게 되므로 건너뛴다). 1단계 출력의 `TASK_EXISTS_BEFORE = YES`로 확인.

3단계 — 숨김 확인(읽기만):

```powershell
Get-ScheduledTask -TaskName "InvestmentV2-*", "GuardedPortfolio-SEC-Shadow-v0.1" -ErrorAction SilentlyContinue | ForEach-Object { $_.TaskName + " : " + $_.Actions[0].Arguments }
```

2단계에서 다시 등록한 작업(InvestmentV2-AutoCore, -AutoCoreDecide, -HostStatus, -JournalScore, -OffsiteBackup, -T2rcCheck, GuardedPortfolio-SEC-Shadow-v0.1)의 줄이 `-WindowStyle Hidden -NoProfile`로 시작하면 끝. 그 밖의 InvestmentV2-* 작업(예: DevQueue, DocsCommit)은 이번 범위 밖이라 예전 인자 그대로 보인다(확인 필요: 그 작업들도 창이 뜨는지는 이번에 보지 않음).
