---
id: runner-fix-report
title: run_auto_core.ps1 Python 찾기 변수가 -Command 인자를 덮어쓰는 버그 수정 — Builder 보고
date: 2026-10-13
prompt: docs/claude/runner-fix-builder-prompt.md
base: 6012f2f (작업 트리, 커밋 안 함)
authority: order_authority=false · quantity_authority 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음 · 예약 작업 변경 없음
---

## 1. 바꾼 줄 (manage-us-stock-strategy/scripts/run_auto_core.ps1, +4 / -3)

```
-        $command = Get-Command python.exe -ErrorAction SilentlyContinue
-        if ($null -eq $command) { $command = Get-Command python -ErrorAction SilentlyContinue }
-        if ($null -ne $command) { $PythonPath = $command.Source }
+        # PowerShell variable names ignore case: a name equal to a parameter ($Command) would overwrite it.
+        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
+        if ($null -eq $pythonCommand) { $pythonCommand = Get-Command python -ErrorAction SilentlyContinue }
+        if ($null -ne $pythonCommand) { $PythonPath = $pythonCommand.Source }
```

- 바뀐 것은 변수 이름(`$command` → `$pythonCommand`)과 주석 1줄뿐이다. 인자, 로그 문구(`RUNNER_START`·`RUNNER_FAIL ...`·`RUNNER_END`), 종료 코드 0/1/3, 후보 경로 순서(.venv → venv → PATH), `cmd /c` 줄은 그대로다.
- ASCII만 쓰고 CRLF를 유지했다(수정 전 72줄, 수정 후 73줄 모두 CRLF).

## 2. 새 테스트 manage-us-stock-strategy/tests/test_auto_core_runner.py (8개)

정적 검사(모든 OS, `ParameterShadowStaticTests`)
- `test_checker_catches_the_pre_fix_runner`: 수정 전 runner 조각(`[string]$Command` + `$command = Get-Command ...`)에서 검사 함수가 인자 3개를 뽑고, 대소문자만 다른 대입 2곳을 잡는지 확인한다(검사 함수 자체 확인).
- `test_checker_catches_foreach_and_allows_same_case_reassignment`: `foreach ($symbol in ...)`를 잡고, 대소문자가 같은 재대입(`$Pages = 4`)은 허용하는지 확인한다.
- `test_checker_ignores_function_parameters_and_automatic_values`: 함수 안 `param(...)`과 `$true`는 스크립트 인자로 세지 않고, 함수가 먼저 나오면 스크립트 인자가 없는 것으로 보는지 확인한다.
- `test_auto_core_powershell_files_never_overwrite_a_parameter`: `run_auto_core.ps1`·`collect_30m.ps1`·`register_auto_core_task.ps1`의 인자 목록을 정확히 확인하고, 대소문자만 다른 대입이 0개인지 확인한다.
- `test_runner_python_lookup_uses_its_own_variable`: runner에 `$pythonCommand` 줄이 있고, 대소문자까지 같은 `$command` 변수는 없는지 확인한다.

동작 검사(Windows이고 `powershell.exe`가 있을 때만 실행, `RunnerCopyBehaviourTests`)
- 임시 폴더 T에 실제 runner의 **복사본**과 가짜 `auto_core.py`(`sys`·`pathlib`만 사용, `sys.argv[1]`을 `T/argv.txt`에 쓰고 종료 코드 0)를 둔다. 실행 전에 두 경로가 T 아래에 있고 저장소 아래에 있지 않은지 단언한다. `-RepositoryRoot`도 T다. `-PythonPath`는 넘기지 않고, PATH 맨 앞에 `dirname(sys.executable)`을 붙인다. 제한 시간은 120초다.
- `test_daily_finds_python_on_path_without_python_path`: 종료 코드 0, `argv.txt` = `daily`, 로그 `auto-core-daily-*.log` 1개에 `RUNNER_START`·`command=daily`·`RUNNER_END exit=0`가 있고 `RUNNER_FAIL`은 없다.
- `test_decide_finds_python_on_path_without_python_path`: decide도 같은 방식으로 확인한다.
- `test_other_command_exits_3_without_running_the_script`: `-Command other`이면 종료 코드 3이고 `argv.txt`가 없다.

저장소의 진짜 `run_auto_core.ps1`·`auto_core.py`를 실행하는 코드는 없다. 진짜 runner는 읽기(정적 검사)와 복사에만 쓴다.

## 3. 결과

| 실행 | 결과 |
|---|---|
| `-p "test_auto_core_runner*.py" -v` (수정 후) | 8개 통과. **동작 테스트 3개는 skip 없이 실제로 돌았다**(Windows, powershell.exe 있음, `... ok` 출력). |
| 같은 테스트, runner를 잠시 수정 전 3줄로 되돌렸을 때 | 4개 실패: 정적 2개(`never_overwrite_a_parameter`, `uses_its_own_variable`), 동작 2개(daily·decide 모두 `3 != 0`, 로그 `RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND` — 10-13 운영 로그와 같은 증상 재현). 확인 뒤 수정본으로 되돌렸다. |
| `-p "test_auto_core*.py"` (전체 auto-core, 수정 후) | 312개 통과, skip 1개. skip은 기존 `test_auto_core_replay.RealDataSmokeTests`이고, 사유는 "saved 30-minute pages exist only in the main checkout"(worktree에 자료가 없음)이다. 이번 변경과 무관하다. |

기존 테스트 파일(`test_auto_core.py`, `test_auto_core_decide.py` 등)은 고치지 않았다. `test_runner_accepts_only_daily_or_decide`, `test_powershell_files_are_ascii`, `NoOrderPathTests`도 통과했다.

## 4. 남은 위험

- 운영 PC의 예약 작업 환경에서 PATH 첫 번째 `python.exe`가 Microsoft Store 별칭(WindowsApps)이면, `Get-Command`가 그 별칭을 고를 수 있다. env-diag-20261013.txt에는 사용자 PATH에 Python 3.13이 있다고 되어 있지만, 실제 순서는 다음 06:15 실행 로그의 `RUNNER_START`/`RUNNER_END`로 확인해야 한다. 실패하면 다시 `RUNNER_FAIL`로 보이고(fail-closed), 별도 수정 대상이 된다.
- 동작 테스트는 이 PC의 사용자 세션에서 돌렸다. 예약 작업(Interactive, Limited)과 환경 변수가 같다는 것을 보장하지는 않는다.
- 새 테스트 파일은 Write 도구로 만들어서 줄바꿈이 LF일 수 있다. 새 .py 파일이라 CRLF 규칙 대상(고치는 기존 파일, 새 .ps1의 ASCII)은 아니다.
- 정적 검사는 정규식 기반이다. 문자열 안의 `$x =`나 `${name}` 형식은 다루지 않는다. 대상 3개 파일에는 해당 형식이 없다.
