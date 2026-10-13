---
id: runner-fix-builder-prompt
title: 자동 코어 실행 스크립트 run_auto_core.ps1 — Python 찾기 변수가 -Command 인자를 덮어쓰는 버그 수정
date: 2026-10-13
class: 권한 경로(run_auto_core.ps1, tests/test_auto_core*.py)를 건드리는 버그 수정(dev-run class authority — 경로 때문. 의미상 권한·한도·주문 단계·수량·관문 불변)
source: docs/claude/redesign-t2-firstrun-report-2026-10-13.md · 사용자 결정 "결정 runner-fix: 승인"(2026-10-13 08:58 KST)
evidence: workspace/outputs/auto-core/logs/auto-core-daily-20261012T211501Z.log, auto-core-decide-20261012T224501Z.log = "RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND" · env-diag-20261013.txt(사용자 PATH에 Python 3.13 있음) · pwsh 재현 "type=String value=pwsh source=[]"
authority: order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 runner-fix -ApproveAuthority — 경로 때문에 붙는 플래그, 사용자 결정 있음)
---

```dev-run
{"task_id": "runner-fix", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 60, "builder_timeout_min": 40, "allowed_paths": ["manage-us-stock-strategy/scripts/run_auto_core.ps1", "manage-us-stock-strategy/tests/test_auto_core_runner.py", "docs/claude/runner-fix-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core): runner python lookup no longer overwrites the -Command parameter (PYTHON_RUNTIME_NOT_FOUND)"}
```

## 목표

Windows 작업 InvestmentV2-AutoCore(06:15 daily)·InvestmentV2-AutoCoreDecide(07:45 decide)가 2026-10-13 첫 운영일에 둘 다 `RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND`로 멈췄다. 원인은 실행 스크립트 한 곳이다. 이 한 곳만 고치고, 같은 종류의 실수를 잡는 테스트를 넣는다.

## 원인 (읽기 전용 확인, base 1bd7bc4)

`manage-us-stock-strategy/scripts/run_auto_core.ps1`

- 5행 `param(... [string]$Command = "daily")` — 실행 인자.
- 47~49행:
  ```
  $command = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($null -eq $command) { $command = Get-Command python -ErrorAction SilentlyContinue }
  if ($null -ne $command) { $PythonPath = $command.Source }
  ```
- PowerShell 변수 이름은 대소문자를 가리지 않는다. `$command`는 `[string]` 형 인자 `$Command`와 **같은 변수**다. CommandInfo가 문자열로 바뀌어 들어가고 `.Source`는 빈 값이 된다. 그래서 `$PythonPath`가 비고 `PYTHON_RUNTIME_NOT_FOUND`로 끝난다. 동시에 `$Command` 값도 "daily"/"decide"에서 다른 문자열로 바뀐다(62행 `$commandLine`이 이 값을 쓴다).
- 저장소에 `.venv`·`venv`가 없어서 이 분기를 반드시 탄다. 수동 실행은 `-PythonPath`를 넘겨서 이 분기를 피했다.
- 같은 패턴 정적 검사: 추적된 .ps1 13개 중 이 파일만 해당(sec_scheduled_shadow_preflight.ps1의 `$persistentUserAgent`는 함수 인자와 스크립트 변수가 다른 범위라 무관 — 이번 작업 범위 밖, 손대지 않는다).

## 바꿀 내용

### A. `run_auto_core.ps1` (최소 수정)

1. 47~49행의 변수 이름을 인자와 겹치지 않는 이름(`$pythonCommand`)으로 바꾼다. 그 밖의 줄은 바꾸지 않는다(로그 문구 `RUNNER_START`·`RUNNER_FAIL ...`·`RUNNER_END`, 종료 코드 0/1/3, 후보 경로 순서, `cmd /c` 방식 그대로).
2. 파일은 ASCII만(기존 테스트 `test_powershell_files_are_ascii`).
3. 주석 한 줄 허용: 왜 이 이름인지(PowerShell 변수 이름은 대소문자 무시 → 인자 이름과 겹치면 안 됨).

### B. 새 테스트 `manage-us-stock-strategy/tests/test_auto_core_runner.py`

1. **정적(모든 OS)**: `run_auto_core.ps1`, `collect_30m.ps1`, `register_auto_core_task.ps1` 각각에서 스크립트 첫 `param(...)` 블록의 인자 이름을 뽑고, 본문에서 그 이름과 **대소문자만 다른** 변수에 값을 넣는 곳(`$name =`, `foreach ($name in`)이 0개인지 확인. 같은 대소문자로 다시 넣는 것(`$PythonPath = ...`)은 허용. 함수 안 `param(...)`은 스크립트 인자 목록에 섞지 않는다. 수정 전 파일(`$command =`)에는 실패하고 수정 후에는 통과해야 한다 — 테스트 안에 수정 전 문자열 조각을 넣어 검사 함수가 그것을 잡는지도 확인한다.
2. **동작(Windows이고 `powershell.exe`가 있을 때만, 아니면 skip)**:
   - 임시 폴더 T에 `T/manage-us-stock-strategy/scripts/`를 만들고, **실제 `run_auto_core.ps1`을 그 폴더로 복사**한다. 같은 폴더에 가짜 `auto_core.py`를 쓴다: `sys.argv[1]`을 `T/argv.txt`에 쓰고 종료 코드 0. 가짜 파일은 표준 라이브러리 `sys`·`pathlib`만 쓴다.
   - **복사본**을 `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File <복사본> -RepositoryRoot <T> -Command daily`로 실행한다(`-PythonPath` 없이). 환경 변수 PATH 맨 앞에 `os.path.dirname(sys.executable)`을 붙인다. 제한 시간 120초.
   - 실행 전에 단언: 복사본 경로와 가짜 `auto_core.py` 경로가 T 아래에 있다. **저장소의 진짜 `run_auto_core.ps1`이나 진짜 `auto_core.py`를 실행하는 코드가 테스트 어디에도 없어야 한다**(진짜 실행 = 키움 조회).
   - 기대: 종료 코드 0, `T/argv.txt` 내용 `daily`, `T/workspace/outputs/auto-core/logs/auto-core-daily-*.log`에 `RUNNER_START`·`command=daily`·`RUNNER_END exit=0`이 있고 `RUNNER_FAIL`은 없다.
   - `decide`도 같은 방식으로 한 번 더(`argv.txt` = `decide`, 로그 이름 `auto-core-decide-*`).
   - 잘못된 인자 `-Command other` → 종료 코드 3, 가짜 auto_core.py가 실행되지 않음(argv.txt 없음).
3. 기존 `test_auto_core.py`·`test_auto_core_decide.py`의 실행 스크립트 테스트(`test_runner_accepts_only_daily_or_decide` 등)는 그대로 통과해야 한다. 기존 테스트 파일은 고치지 않는다.

### C. 보고 `docs/claude/runner-fix-report.md`

바꾼 줄(diff 요약), 새 테스트 목록과 결과, Windows 동작 테스트가 실제로 돌았는지(skip 아님) 여부, 남은 위험.

## 지켜야 할 것 (어기면 Judge FAIL)

1. 진짜 `auto_core.py`·진짜 `run_auto_core.ps1`·`collect_30m.ps1`·`kiwoomcli`·`register_auto_core_task.ps1`을 실행하지 않는다. Windows 예약 작업을 만들거나 바꾸거나 실행하지 않는다.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 들어 있는 줄을 만들거나 지우거나 바꾸지 않는다. 주문 경로 문자열을 쓰지 않는다(`NoOrderPathTests`가 실행 스크립트를 검사한다).
3. 스크립트 ASCII만. Claude Code 설정상 "auto_core.py"가 들어간 명령은 거부되므로 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"` 패턴으로만 돌린다.
4. allowed_paths 밖 파일을 만들거나 고치지 않는다.

## Judge 확인 항목

1. `run_auto_core.ps1` diff가 Python 찾기 변수 이름 변경(+주석 1줄)뿐이고, 인자·로그 문구·종료 코드·후보 순서·`cmd /c` 줄이 그대로다.
2. 바뀐 파일 어디에도 스크립트 인자(`RepositoryRoot`·`PythonPath`·`Command`)와 대소문자만 다른 변수에 값을 넣는 곳이 없다.
3. 정적 테스트가 수정 전 패턴(`$command = Get-Command ...`가 `[string]$Command` 인자와 함께 있는 경우)을 실제로 잡는다(테스트 안 자체 확인이 있다).
4. 동작 테스트가 실행하는 것은 임시 폴더의 복사본과 가짜 auto_core.py뿐이다. 저장소 진짜 스크립트를 실행하는 경로가 없다. `-RepositoryRoot`도 임시 폴더다.
5. 동작 테스트가 Windows에서 skip되지 않고 돌았다는 증거가 보고서 또는 테스트 출력에 있다(skip이면 이유가 적혀 있다).
6. 주문·권한·정책·상태 파일 변경 없음, 키움 호출 없음, 예약 작업 변경 없음.
7. 기존 테스트 파일 무변경, `test_auto_core*.py` 전부 통과.
