---
id: runner-deps-builder-prompt
title: 자동 코어 실행기 — 시작 전 Python 시간대 자료(tzdata) 점검, 없으면 이름 있는 실패 줄(Python 판 포함)·종료 코드 4
date: 2026-11-13
class: 권한 경로(run_auto_core.ps1 — authority-paths.txt 22행) 실행기 보강(dev-run class authority — 경로 때문. 의미상 권한·한도·주문 단계·대조 불변식·킬 스위치 불변)
source: docs/claude/code-review-2026-11-13.md 1절 M-1·2절 #3 · 실제 사례 2026-11-10 06:15·07:45 자동 코어가 C:\Python315(tzdata 없음)에서 `ZoneInfoNotFoundError: Asia/Seoul`로 import 단계에서 죽어 그날 기록이 아예 없음(workspace/outputs/auto-core/logs/auto-core-daily-20261109T211501Z.log)
authority: order_authority=false · quantity_authority 값 변경 없음 · 주문 경로 없음 · 정책·상태 파일 쓰기 없음 · 키움 호출 없음 · 예약 작업 등록 변경 없음
approval: 사장 결정 카드 "급한 2건 + 실행기 점검 착수" 2026-11-13 14:40:53 KST(code-review-2026-11-13.md 6절 — 범위 M-1 개발 큐)
weekly_user_touch: 1 (병합 1번: .\tools\dev-merge.ps1 runner-deps -ApproveAuthority — 경로 때문에 붙는 플래그. 다른 dev-run이 돌고 있으면(_lock) 병합하지 않는다)
queue_order: bar-isolate 병합 뒤에 큐에 올린다(둘 다 docs/claude 밖을 바꿔 같은 기준에서 돌면 나중 병합이 STOP_BASE_MOVED — devpipe.py 2028~2030행)
---

```dev-run
{"task_id": "runner-deps", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 50, "builder_timeout_min": 40, "allowed_paths": ["manage-us-stock-strategy/scripts/run_auto_core.ps1", "manage-us-stock-strategy/tests/test_auto_core_runner_deps.py", "docs/claude/runner-deps-report.md"], "target_tests": ["test_auto_core_runner*.py"], "commit_message": "fix(auto-core): runner checks the Python time zone data before starting the core (named RUNNER_FAIL line with the Python version, exit 4)"}
```

## 목표

자동 코어의 Python 바깥 의존성은 Windows의 시간대 자료(tzdata) 하나다(`auto_core_reconcile.py` 38행, `auto_core_decide.py` 41행이 `zoneinfo.ZoneInfo`를 import 단계에서 씀. 그 밖 import는 표준 라이브러리와 저장소 모듈).

2026-11-07~11-09 사이 기본 Python이 3.15로 바뀌었다. 그 Python에 tzdata가 없어서 11/10 두 실행이 기록 없이 죽었다. 원인은 실행기 로그의 파이썬 traceback에서만 보였다.

고칠 것: 실행기(`run_auto_core.ps1`)가 auto_core.py를 부르기 전에 같은 Python으로 시간대 두 개를 읽어 본다. 실패하면 Python 판을 담은 이름 있는 실패 줄을 남기고 종료 코드 4로 끝낸다. 성공한 날의 로그·출력은 지금과 같다.

범위를 코드 리뷰 2절 #3보다 줄인 것(의도):
- 그날 FAIL 기록(result.json)은 쓰지 않는다. 결과 스키마의 필수 칸 23개를 PowerShell에서 다시 만들면 코어 논리가 둘로 갈린다. 같은 날 알림은 기존 ①"daily 결과 없음"(auto-core-alert.txt 36행)이 내고, 원인은 이름 있는 실패 줄로 바로 보인다.
- run_llm_pilots.ps1은 넣지 않는다. 시범 SDK는 시범 실행 안에서 늦게 import되고(llm_pilot_common.py 95행) 실패가 그날 기록(failed.md)에 남는다. 그 기록을 읽는 곳이 없는 문제는 M-2(기록만)다.

## 바꿀 것 — `manage-us-stock-strategy/scripts/run_auto_core.ps1`

1. Python 경로를 정한 뒤(지금 53~56행 `RUNNER_FAIL PYTHON_RUNTIME_NOT_FOUND` 검사 다음), `RUNNER_START` 줄 앞에서 사전 점검을 한 번 한다.
   - 명령: `& $PythonPath -c $code 2>&1`로 바로 부른다(`cmd /c` 문자열로 조립하지 않는다).
   - 코드 안 문자열은 **작은따옴표만** 쓴다. Windows PowerShell 5.1은 외부 프로그램 인자 속 큰따옴표를 이스케이프하지 않아 코드가 깨진다. 예: `import sys; print('%d.%d.%d' % sys.version_info[:3], flush=True); import zoneinfo; zoneinfo.ZoneInfo('Asia/Seoul'); zoneinfo.ZoneInfo('America/New_York')`
   - 판 줄은 `flush=True`로 먼저 찍는다. 파이프에서는 stdout이 블록 버퍼링되어, 안 그러면 실패 때 traceback 뒤로 밀리거나 늦게 나온다.
   - Python에 `-I`·`-s`·`-E`·`-S`를 붙이지 않는다. tzdata가 사용자 site-packages(AppData\Roaming\Python\Python315)에 있으므로, 붙이면 거짓 실패가 난다.
   - 실행은 지금 auto_core.py 호출(60~73행)처럼 `$ErrorActionPreference`를 잠시 "Continue"로 두고 한다. Windows PowerShell 5.1은 Stop 상태에서 native stderr를 예외로 바꾼다.
   - 출력·오류는 변수로 받아 실행기 로그에만 남긴다. 새 파일·화면 출력은 만들지 않는다.
2. 사전 점검의 종료 코드가 0이 아니면 다음과 같이 한다.
   - `RUNNER_FAIL PYTHON_DEPS_MISSING zoneinfo=Asia/Seoul,America/New_York python=<판>`을 쓴다. 판은 출력 가운데 문자열(stdout) 줄에서 `^\d+\.\d+\.\d+$`에 맞는 첫 줄이다. 없으면 `python=unknown`이다.
   - 그 뒤에 Python 오류의 마지막 줄을 300자 이내로 한 줄 더 쓴다. ASCII가 아닌 글자는 `?`로 바꾼다(run_llm_pilots.ps1 84행 방식).
   - `exit 4`로 끝낸다. 이때 auto_core.py는 부르지 않고 `RUNNER_START`도 쓰지 않는다.
3. 성공하면(종료 코드 0) 지금처럼 `RUNNER_START`를 쓰고 auto_core.py를 부른다. `RUNNER_START` 줄은 바꾸지 않는다. Python 경로는 어느 줄에도 쓰지 않는다(한글 경로가 ASCII 로그에서 깨짐).
4. 머리 주석(13~14행)의 종료 코드 설명에 "4 when the Python runtime cannot load the time zone data (tzdata missing) - the run did not start"를 더한다(ASCII).

그 밖은 바꾸지 않는다.
- `-Command` 검사(`exit 3`, 첫 분기)는 그대로 둔다.
- Python 찾는 순서(.venv → venv → PATH)·로그 경로·이름, auto_core.py 호출과 그 종료 코드 전달도 그대로 둔다.
- 예약 등록 스크립트(`register_auto_core_task.ps1`)는 고치지 않는다.

## 새 테스트 — `manage-us-stock-strategy/tests/test_auto_core_runner_deps.py`

정적 테스트(모든 OS):
1. 실행기가 ASCII이고 다음을 모두 담는다: `RUNNER_FAIL PYTHON_DEPS_MISSING`, `exit 4`, `Asia/Seoul`, `America/New_York`, `python=`. `RUNNER_START` 줄 문자열은 지금과 같다.
2. 사전 점검 줄에 ` -I `·` -s `·` -E `·` -S `가 없다.
3. `-Command` 검사(`exit 3`)가 사전 점검보다 앞에 있고, 사전 점검이 `RUNNER_START`보다 앞에 있다(문자열 위치 비교).

동작 테스트(Windows·powershell.exe만, `test_auto_core_runner.py` 143~198행 `RunnerCopyBehaviourTests`처럼 임시 폴더에 실행기 사본과 가짜 auto_core.py를 둔다. 저장소 파일은 실행하지 않는다):

4. 실패 경로: `-PythonPath`로 가짜 실행 파일을 넘긴다. 예를 들어 첫 인자가 `-c`이면 `exit /b 1`하는 임시 `.cmd`.
   - 확인할 것: 종료 코드 4, 로그에 `RUNNER_FAIL PYTHON_DEPS_MISSING`·`python=unknown`, `RUNNER_START` 없음, 가짜 auto_core.py가 불리지 않음(argv 파일 없음).
   - daily와 decide 둘 다 확인한다.
   - 하나 더: 가짜 `.cmd`가 `echo 3.15.2` 뒤 `exit /b 1` → 로그에 `python=3.15.2`.
5. 성공 경로: 테스트를 돌리는 Python(`sys.executable`)을 넘긴다.
   - 확인할 것: 종료 코드 0, `RUNNER_START`·`RUNNER_END exit=0` 있음, `RUNNER_FAIL` 없음, 가짜 auto_core.py가 불림.
6. `-Command other`면 지금처럼 3으로 끝나고 사전 점검도 하지 않는다. 가짜 실패 Python을 넘겨도 3이다.

키움·kiwoomcli·실제 auto_core.py·예약 작업을 부르는 테스트는 만들지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)

1. diff는 run_auto_core.ps1, 새 테스트 파일, 보고뿐이다. 기존 테스트는 고치지 않는다.
   - 기존 테스트가 실패하면 고치지 말고 BLOCKED로 보고한다.
   - 특히 지켜야 할 것: `test_auto_core_runner.py`(매개변수 이름과 같은 변수 금지 — 대소문자 무시, `$pythonCommand` 줄 2개, 187~191행 PATH의 진짜 Python으로 `RUNNER_END exit=0`), `test_auto_core_decide.py` 1450~1464행(`-Command` 검사 줄·로그 이름 줄), `test_auto_core.py` 1570~1585행(주문 문자열 없음·ASCII).
2. 주문 경로 문자열(`/api/us/ordr`, `ust2000x`, `kiwoom_order`, `order_submit`, `place_order`, `kt1000x`)을 넣지 않는다. 키움·예약 작업·정책·상태 파일을 건드리지 않는다.
   - `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch` 글자가 든 줄을 어느 파일에도 만들거나 바꾸지 않는다. 보고 머리말도 같다(이 지시문 머리말의 authority 줄을 옮기지 말고 '권한 표지 4종 줄 변경 없음 · 주문 경로 없음 · 키움 호출 없음'처럼 쓴다). 선례: bar-isolate 1회차 Judge FAIL(docs/claude/dev-runs/bar-isolate.md).
3. 실행하지 않는다: 저장소의 run_auto_core.ps1·auto_core.py·register_auto_core_task.ps1(테스트는 임시 사본만 실행).
   - 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"` 형식 그대로만 돌린다(앞에 환경 변수나 플래그를 붙이지 않는다). 전체 테스트는 돌리지 않는다.
4. run_auto_core.ps1(git i/lf, 작업 트리 CRLF)의 줄바꿈을 지킨다. 파일은 ASCII 전용이다.

## 보고 `docs/claude/runner-deps-report.md`

보고에 넣을 것:
- 바꾼 줄(파일:줄)과 새 테스트 목록.
- 연결표(아래 절)를 옮기고 ②③⑤ 칸마다 파일:행 또는 trig id를 쓴다. 근거가 없으면 '끊김(메울 변경·승인 경로)'로 쓴다(bar-isolate 1회차 Judge FAIL 사유).
- 대상 테스트 결과(Ran 수, 실패 0, 건너뜀 수 — Windows 동작 테스트가 실제로 돌았는지)와 `git diff --ignore-cr-at-eol --stat`.
- 남은 위험:
  - 점검은 시간대 자료만 본다. 저장소 모듈 import 오류는 지금처럼 실행 중 traceback으로만 보인다.
  - 같은 Python을 쓰는 다른 예약 작업(LLM 시범·개발 큐 등)은 이 점검 밖이다.

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 실행기 로그 줄 `RUNNER_FAIL PYTHON_DEPS_MISSING … python=<판>`·종료 코드 4(기존 로그 파일 workspace/outputs/auto-core/logs/auto-core-<명령>-<UTC>.log, 새 파일 없음) | 예약 InvestmentV2-AutoCore 06:15·AutoCoreDecide 07:45 KST(`register_auto_core_task.ps1` 25·27행) → `run_auto_core.ps1` 사전 점검(이번 변경) | 같은 날: 자동 운영 코어 결과 알림 trig_01D5KxMSJgbeRG1ZL5ox3Fna 08:50(`auto-core-alert.txt` 36행 ① "daily 결과 없음" — 기존). 다음 날: PC 상태 점검 05:50(`host_status.ps1` 20행 코어 작업 목록·142~145행 '7일 안 마지막 결과 0 아님 → WARN') → 같은 알림 49행 ⑭ | 사장 알림 → Cowork(사람 단계)가 로그의 이름 있는 실패 줄로 원인·Python 판을 바로 앎 → 사장 터미널 설치 한 줄 안내(11/10 같은 진단 시간 단축). 코어 판정·주문표는 불변 | 알림 예약이 안 돌거나 실패하면 사장실 결과 모음 trig_01GrAs6UCfspeTBK3mMncyrd(월~토 09:35)·trig_01XChapmUEKxAcjKF9AFiERJ(일 10:05)(`docs/claude/active-decisions.md` 62행)이 이름을 올림(`docs/claude/scheduled-prompts/room-digest.txt` 2행·5행 list_triggers last_run·28행 '안 돎·늦음·실패'). PC 상태 점검 결과가 없으면 같은 알림 ⑭(`docs/claude/scheduled-prompts/auto-core-alert.txt` 49행 "PC 상태 점검 결과 없음(05:50 미실행)"). 실행기 회귀는 새 테스트 4·5(Builder가 보고 연결표에 `test_auto_core_runner_deps.py` 파일:행으로 적음) | 연결 |

## Judge 확인 항목

1. diff가 run_auto_core.ps1(사전 점검·실패 줄·`exit 4`·머리 주석), 새 테스트 파일, 보고뿐이다. 기존 테스트·등록 스크립트·주문 경로·정책·상태 변경이 없다.
2. 사전 점검이 `-Command` 검사 뒤, `RUNNER_START`·auto_core.py 호출 앞에 있다. 실패하면 auto_core.py가 불리지 않는다(테스트 4).
2-1. 사전 점검 Python 코드에 큰따옴표가 없고(작은따옴표만), 판 줄은 `flush=True`이며, 판은 stdout 줄에서 형식에 맞는 첫 줄로 읽는다.
3. 사전 점검 Python 호출에 `-I`·`-s`·`-E`·`-S`가 없다(사용자 site-packages의 tzdata를 봐야 함).
4. 성공 경로의 `RUNNER_START` 줄·auto_core.py 호출·종료 코드 전달·로그 이름이 그대로다(기존 `test_auto_core_runner.py` 통과, 테스트 5).
5. 새 테스트가 바뀐 동작을 실제로 잡는다. 사전 점검을 빼면 테스트 4가 실패한다. Windows 동작 테스트가 건너뛰어지지 않고 돌았는지 보고에서 확인한다.
6. 대상 테스트가 전부 통과한다.
7. G9: 연결표 ②③⑤의 원문 행 대조 — register_auto_core_task.ps1 25·27행, auto-core-alert.txt 36·49행, host_status.ps1 20·142~145행, active-decisions.md 62행, room-digest.txt 2·5·28행, 새 테스트 4·5의 파일:행. 칸마다 파일:행·trig id 또는 '끊김(메울 변경·승인 경로)'이 있어야 한다.
