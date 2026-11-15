---
id: runner-deps-report
title: runner-deps Builder 보고 — 자동 코어 실행기 시간대 자료(tzdata) 사전 점검
date: 2026-11-14
prompt: docs/claude/runner-deps-builder-prompt.md
scope: run_auto_core.ps1 · 새 테스트 test_auto_core_runner_deps.py · 이 보고
safety: 권한 표지 4종 줄 변경 없음 · 주문 경로 없음 · 키움 호출 없음 · 정책·상태 파일 변경 없음 · 예약 등록 변경 없음
---

# runner-deps Builder 보고

## 1. 바꾼 줄 — `manage-us-stock-strategy/scripts/run_auto_core.ps1`

| 줄 | 내용 |
|---|---|
| 14~15 | 머리 주석 종료 코드 설명에 `4 when the Python runtime cannot load the time zone data (tzdata missing) - the run did not start.` 추가(14행 끝 `.`→`;`, 15행 새 줄) |
| 58~62 | 사전 점검 이유 주석(ASCII) |
| 64 | `$depsCode` — 작은따옴표만 쓰는 Python 코드. 판 줄을 `flush=True`로 먼저 찍고 `zoneinfo.ZoneInfo('Asia/Seoul')`·`zoneinfo.ZoneInfo('America/New_York')`를 읽음 |
| 67~76 | `$ErrorActionPreference`를 잠시 `Continue`로 두고 `& $PythonPath -c $depsCode 2>&1`(70행)로 같은 Python을 바로 부름. 격리 플래그 없음, `cmd /c` 조립 없음. 실행 자체가 예외면 실패로 봄(fail-closed) |
| 77~101 | 종료 코드가 0이 아니거나 없으면: 판 = stdout 줄 중 `^\d+\.\d+\.\d+$`에 맞는 첫 줄(없으면 `unknown`), 오류 = 마지막 stderr 줄(없으면 마지막 다른 stdout 줄, 그것도 없으면 `exit=<코드>`)을 줄바꿈 제거·ASCII 밖 글자 `?`·300자 자름(run_llm_pilots.ps1 84~85행 방식). 98행 `RUNNER_FAIL PYTHON_DEPS_MISSING zoneinfo=Asia/Seoul,America/New_York python=<판>`, 99행 `RUNNER_FAIL_DETAIL <오류 줄>`, 100행 `exit 4`. auto_core.py 호출·`RUNNER_START` 없음 |
| 103~ | 그대로: `RUNNER_START` 줄(104행, 문자열 불변), auto_core.py 호출(`cmd /c $commandLine`), `RUNNER_END`, 종료 코드 전달 |

바꾸지 않은 것: `-Command` 검사(`exit 3`, 18~20행 첫 분기), Python 찾는 순서(.venv → venv → PATH), 로그 경로·이름, auto_core.py 호출, `register_auto_core_task.ps1`, 기존 테스트. Python 경로는 어느 로그 줄에도 쓰지 않음. 작업 트리 줄바꿈 CRLF 유지(`git ls-files --eol` → `i/lf w/crlf`), 파일 ASCII 전용(기존 `test_powershell_files_are_ascii` 2곳 통과).

## 2. 새 테스트 — `manage-us-stock-strategy/tests/test_auto_core_runner_deps.py`

정적(모든 OS) — `RunnerDepsStaticTests`(60행):
1. `test_runner_is_ascii_and_names_the_failure`(61행): ASCII 디코드, `RUNNER_FAIL PYTHON_DEPS_MISSING`·`exit 4`·`Asia/Seoul`·`America/New_York`·`python=` 포함, `RUNNER_START` 줄 문자열이 기존과 같고 1개.
2. `test_precheck_runs_the_same_python_without_isolation_flags`(69행): 사전 점검 호출 줄이 1개, `& $PythonPath -c $depsCode 2>&1`, `cmd /c` 아님, ` -I `·` -s `·` -E `·` -S ` 없음.
3. `test_precheck_code_uses_single_quotes_and_flushes_the_version_first`(80행): 코드에 큰따옴표·백틱 없음, 판 줄 `flush=True`가 `import zoneinfo`보다 앞, 두 시간대.
4. `test_order_is_command_check_then_precheck_then_start_then_core`(92행): `-Command` 검사(`exit 3`) < 사전 점검 < 실패 줄 < `exit 4` < `RUNNER_START` < auto_core.py 호출(문자열 위치).

동작(Windows·powershell.exe만, 임시 폴더의 실행기 사본 + 가짜 auto_core.py + 가짜 Python `.cmd`) — `RunnerDepsCopyBehaviourTests`(109행):
5. `test_daily_without_time_zone_data_exits_4_and_never_starts_the_core`(170행), `test_decide_…`(173행): 첫 인자가 `-c`면 `exit /b 1`하는 가짜 Python → 종료 코드 4, 로그에 `RUNNER_FAIL PYTHON_DEPS_MISSING … python=unknown`, `RUNNER_START`·`RUNNER_END` 없음, argv 파일 없음(가짜 코어 안 불림), 로그 2줄·ASCII.
6. `test_failure_line_carries_the_python_version_and_the_last_error_line`(176행): 가짜 Python이 `echo 3.15.2` + stderr 한 줄 뒤 `exit /b 1` → `python=3.15.2`, 둘째 줄에 `ZoneInfoNotFoundError`.
7. `test_python_with_time_zone_data_runs_the_core_as_before`(181행): `-PythonPath sys.executable` → daily·decide 각각 종료 코드 0, `RUNNER_START`·`RUNNER_END exit=0`, `RUNNER_FAIL` 없음, 가짜 코어가 그 명령으로 불림.
8. `test_other_command_exits_3_before_the_precheck`(196행): 가짜 실패 Python을 넘겨도 `-Command other` → 3, 로그·workspace 폴더 없음.

사전 점검을 빼면: 가짜 `.cmd`는 `-c`가 아닌 인자에는 `exit /b 0`이므로 실행기가 가짜 코어를 부르고 0으로 끝나 테스트 5·6이 실패한다(종료 코드 4 단언, argv 파일 없음 단언).

## 3. 테스트 결과

- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_runner*.py" -v` → **Ran 17, OK, 실패 0, 건너뜀 0**. 새 Windows 동작 테스트 5개와 기존 `RunnerCopyBehaviourTests` 3개가 모두 실제로 돌았다(-v 출력에 각각 `ok`). 이 PC의 테스트 Python에는 tzdata가 있어 성공 경로가 통과했다.
- 참고(지켜야 할 기존 테스트 확인): `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` → **Ran 631, OK (skipped=1)**, 실패 0. `test_auto_core_decide.py` `WindowsTaskTests`(1452~1463행)·`test_auto_core.py` `NoOrderPathTests`(1570~1584행) 포함. 전체 테스트는 돌리지 않았다.
- `git diff --ignore-cr-at-eol --stat`(새 파일은 추적 전이라 stat에 안 나옴 — `git status`에 `?? manage-us-stock-strategy/tests/test_auto_core_runner_deps.py`):

```
 manage-us-stock-strategy/scripts/run_auto_core.ps1 | 48 +++++++++++++++++++++-
 1 file changed, 47 insertions(+), 1 deletion(-)
```

## 4. 연결표 (지시문 연결표를 옮기고 ②③⑤ 칸마다 근거를 붙임)

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 실행기 로그 줄 `RUNNER_FAIL PYTHON_DEPS_MISSING … python=<판>`·`RUNNER_FAIL_DETAIL`·종료 코드 4(기존 로그 파일 workspace/outputs/auto-core/logs/auto-core-<명령>-<UTC>.log, 새 파일 없음) | 예약 InvestmentV2-AutoCore 06:15·InvestmentV2-AutoCoreDecide 07:45 KST — `manage-us-stock-strategy/scripts/register_auto_core_task.ps1:25`·`:27` → `run_auto_core.ps1:64-101` 사전 점검(이번 변경, 실패 줄 98·99행, `exit 4` 100행) | 같은 날: 자동 운영 코어 결과 알림 trig_01D5KxMSJgbeRG1ZL5ox3Fna 08:50 — `docs/claude/scheduled-prompts/auto-core-alert.txt:36` ① "daily 결과 없음(미실행·진행 중) — 확인 필요"(기존). 다음 날: PC 상태 점검 05:50 — `manage-us-stock-strategy/scripts/host_status.ps1:20` 코어 작업 목록(InvestmentV2-AutoCore·AutoCoreDecide)·`:142-145` 7일 안 마지막 결과 0 아님 → WARN(종료 코드 4 = 0x00000004) → 같은 알림 `auto-core-alert.txt:49` ⑭ | 사장 알림 → Cowork(사람 단계)가 로그의 이름 있는 실패 줄로 원인·Python 판을 바로 앎 → 사장 터미널 설치 한 줄 안내(11/10 같은 진단 시간 단축). 코어 판정·주문표는 불변 | 알림 예약이 안 돌거나 실패하면 사장실 결과 모음 trig_01GrAs6UCfspeTBK3mMncyrd(월~토 09:35)·trig_01XChapmUEKxAcjKF9AFiERJ(일 10:05)(`docs/claude/active-decisions.md:62`)이 이름을 올림(`docs/claude/scheduled-prompts/room-digest.txt:2` 목적 "돌았는지"·`:5` list_triggers last_run·`:28` '안 돎·늦음·실패'). PC 상태 점검 결과가 없으면 같은 알림 ⑭(`docs/claude/scheduled-prompts/auto-core-alert.txt:49` "PC 상태 점검 결과 없음(05:50 미실행)"). 실행기 회귀는 새 테스트 — `manage-us-stock-strategy/tests/test_auto_core_runner_deps.py:170`·`:173`·`:176`(테스트 4 실패 경로), `:181`(테스트 5 성공 경로), `:196`(테스트 6), 정적 `:61`·`:69`·`:80`·`:92` | 연결 |

원문 대조(이 세션에서 열어 확인): register_auto_core_task.ps1 25·27행 = 두 작업 이름·06:15/07:45·`daily`/`decide`; auto-core-alert.txt 36행 = ①, 49행 = ⑭; host_status.ps1 20행 = `$coreTaskNames`, 142~145행 = 마지막 결과 0 아님·7일 안 → WARN; active-decisions.md 62행 = 결과 모음 두 예약 trig id; room-digest.txt 2·5·28행 = 위 인용.

## 5. 남은 위험

- 점검은 시간대 자료만 본다. 저장소 모듈 import 오류는 지금처럼 실행 중 traceback으로만 보인다.
- 같은 Python을 쓰는 다른 예약 작업(LLM 시범·개발 큐 등)은 이 점검 밖이다.
- 그날 FAIL 기록(result.json)은 쓰지 않는다(지시문의 의도된 범위 축소). 같은 날 알림은 기존 ①이 낸다.
- 실행마다 Python을 한 번 더 띄운다(사전 점검). 그 출력은 변수에만 남고 성공한 날 로그는 이전과 같다.
