---
id: hide-task-window-builder-prompt
title: 예약 작업 창 숨김 — 실행 중 키 입력(Ctrl+C)으로 자동 코어가 끊기지 않게
date: 2026-10-21
class: 작업 등록 스크립트(.ps1) 실행 인자 한 곳씩 + 정적 테스트. 판단·권한·한도·주문 단계·수량·관문 불변
source: 사용자 결정 "수정 제안 진행"(2026-10-21 Cowork 세션)
evidence: workspace/outputs/auto-core/logs/auto-core-decide-20261020T224500Z.log = "RUNNER_START ... command=decide" 다음 줄바꿈 없는 "^C", RUNNER_END 없음, 파일 수정 2026-10-21 07:58:02 KST · register_auto_core_task.ps1:83-91(Interactive logon, 창 숨김 없음) · auto_core_decide.py:64 RESEARCH_WAIT_UNTIL = 08:30(창이 최대 45분 열림) · 실행 시간 제한 60분(08:45)이라 시간 초과 아님 · 같은 날 05:50 host-status power_sleep·pending_reboot OK
authority: order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음
weekly_user_touch: 0 (병합 1번 + 작업 다시 등록 1번 — 사용자 결정 있음)
---

```dev-run
{"task_id": "hide-task-window", "class": "authority", "builder_model": "sonnet", "builder_effort": "medium", "max_turns": 60, "builder_timeout_min": 40, "allowed_paths": ["manage-us-stock-strategy/scripts/register_auto_core_task.ps1", "manage-us-stock-strategy/scripts/register_host_status_task.ps1", "manage-us-stock-strategy/scripts/register_journal_score_task.ps1", "manage-us-stock-strategy/scripts/register_offsite_backup_task.ps1", "manage-us-stock-strategy/scripts/register_sec_scheduled_shadow_task.ps1", "docs/claude/t2rc-register-task.ps1", "manage-us-stock-strategy/tests/test_task_window_hidden.py", "docs/claude/hide-task-window-report.md"], "target_tests": ["test_task_window_hidden.py", "test_auto_core*.py", "test_host_status_static.py", "test_journal_score_task_static.py", "test_offsite_backup_static.py", "test_sec_scheduled_shadow.py"], "commit_message": "fix(tasks): start scheduled PowerShell tasks with -WindowStyle Hidden so keyboard Ctrl+C cannot stop them"}
```

## 목표

2026-10-21 07:45 InvestmentV2-AutoCoreDecide가 07:58에 `^C`로 끊겨 판정이 없었다. 작업은 로그인 사용자 화면(Interactive)에서 PowerShell 창을 띄운 채 돌고, decide는 연구 기록을 08:30까지 기다리므로 창이 오래 열려 있다. 그 창에 들어간 키 입력(Ctrl+C)이 가장 유력한 원인이다(작업 기록 결과 코드는 사용자 확인 필요). 예약 작업의 PowerShell 창을 숨겨 키 입력을 받지 않게 한다. 다른 것은 바꾸지 않는다.

## 바꿀 내용

### A. 작업 등록 스크립트 6개 (각 한 곳)

대상: `register_auto_core_task.ps1`(83행), `register_host_status_task.ps1`(79행), `register_journal_score_task.ps1`(80행), `register_offsite_backup_task.ps1`(80행), `register_sec_scheduled_shadow_task.ps1`(138행), `docs/claude/t2rc-register-task.ps1`(75행).

1. `$actionArguments` 문자열 **맨 앞**에 `-WindowStyle Hidden `을 붙인다. 결과 예: `'-WindowStyle Hidden -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" ...'`. 기존 테스트가 `"-NoProfile -NonInteractive -ExecutionPolicy Bypass -File"` 부분 문자열을 확인하므로 그 순서는 그대로 둔다(PowerShell은 `-WindowStyle`이 `-File` 앞에 있어야 한다).
2. PlanOnly 출력(Write-TaskPlan 등)에 ACTION이나 인자를 찍는 곳이 있으면 같은 문자열을 쓰게 둔다(새 항목 추가는 `WINDOW_STYLE = HIDDEN` 한 줄까지 허용).
3. 그 밖은 바꾸지 않는다: LogonType Interactive, RunLevel Limited, 트리거 시각·요일, ExecutionTimeLimit, MultipleInstances, StartWhenAvailable, WakeToRun, 작업 이름, 실행 래퍼 경로.
4. 주석 한 줄 허용(왜 숨기나: 화면에 뜬 창에 Ctrl+C가 들어가 2026-10-21 decide가 끊김).
5. 파일 ASCII만(기존 `test_powershell_files_are_ascii` 류).
6. `conhost --headless` 등 다른 방식은 쓰지 않는다(가장 단순한 한 가지). 실행 래퍼(`run_auto_core.ps1`, `t2rc-check-run.ps1` 등)는 고치지 않는다.

### B. 새 테스트 `manage-us-stock-strategy/tests/test_task_window_hidden.py` (정적, 모든 OS)

1. 위 6개 파일 각각에서 `$actionArguments =` 줄을 찾아, 따옴표 안 문자열이 `-WindowStyle Hidden -NoProfile -NonInteractive -ExecutionPolicy Bypass -File`로 시작하는지 확인.
2. 각 파일에 `-LogonType Interactive`와 `-RunLevel Limited`가 그대로 있는지 확인(숨김 때문에 다른 로그온 방식으로 바꾸지 않았음).
3. 검사 함수가 수정 전 문자열(`'-NoProfile -NonInteractive ...'`로 시작)을 실패로 잡는지 테스트 안에서 자체 확인.
4. 작업 등록 스크립트를 실행하지 않는다(파일을 텍스트로만 읽는다).

### C. 보고 `docs/claude/hide-task-window-report.md`

파일별 바뀐 줄, 테스트 결과, 남은 위험(창이 숨겨지기 전 잠깐 깜빡일 수 있음, 작업이 멈춰도 화면에서 안 보임 — 로그·알림으로만 확인), 사용자가 병합 뒤 할 일: 관리자 아닌 일반 PowerShell에서 각 등록 스크립트를 다시 실행하는 명령 목록(스크립트의 기존 인자 그대로, PlanOnly로 먼저 확인하는 순서).

## 지켜야 할 것 (어기면 Judge FAIL)

1. 작업 등록 스크립트·실행 래퍼·`auto_core.py`·`kiwoomcli`를 실행하지 않는다. Windows 예약 작업을 만들거나 바꾸거나 실행하지 않는다.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 들어 있는 줄을 만들거나 지우거나 바꾸지 않는다. 주문 경로 문자열을 쓰지 않는다.
3. 기존 테스트 파일은 고치지 않는다. 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"`으로만 돌린다("auto_core.py"가 들어간 명령 금지).
4. allowed_paths 밖 파일을 만들거나 고치지 않는다.

## Judge 확인 항목

1. 6개 파일 diff가 각각 `$actionArguments` 앞쪽 `-WindowStyle Hidden ` 추가(+주석 1줄, PlanOnly 한 줄 허용)뿐이다.
2. 로그온 방식·권한 수준·트리거·시간 제한·중복 실행·작업 이름이 그대로다.
3. 새 정적 테스트가 수정 전 문자열을 실제로 잡는다(자체 확인이 있다).
4. 주문·권한·정책·상태 파일 변경 없음, 키움 호출 없음, 예약 작업 변경·실행 없음.
5. 기존 테스트 파일 무변경, target_tests 전부 통과(기준선 대비 새 실패 0).
