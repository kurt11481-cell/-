# devq-api Builder 보고 — 개발 큐 Judge를 API 크레딧(Agent SDK) 경로로 (1단계 Judge만)

- 작성: 2026-11-25 KST, 수동 경로 Builder(회사PC worktree, 브랜치 `worktree-devq-api`, 기준 커밋 113727c5d66bb4d47c081d33e3a5af18121171ed).
- 지시문: docs/claude/devq-api-builder-prompt.md(메인 체크아웃, 미추적) · 제안서 docs/claude/devq-api-proposal-2026-11-25.md 2절.
- 결론: 허용 파일 7개 + 이 보고만 바꿈. 시험 두 줄 모두 통과. 스위치는 꺼진 채(`judge_enabled: false`). 권한 표지 4종 줄 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음 · 키 값을 읽거나 출력하지 않음.
- 하지 않은 것: pip 설치, 실제 SDK·API 호출, dev-run·dev-queue·dev-merge 실행, git add·commit·push·병합, 사용자 환경 변수 읽기·바꾸기, 비밀 파일 열기, `.claude/`·CLAUDE.md·정책·상태 파일 수정.

## (a) 바꾼 함수·줄 (파일:행, 이 worktree 기준)

| 파일 | 위치 | 내용 |
|---|---|---|
| tools/dev_pipeline/devpipe.py | 22·24 | `import importlib.util`·`import math` |
| 〃 | 108~126 | devq-api 상수: `API_ROUTE_REL`·승인 기록 정규식 2개·끄기/닫힘/장부 파일 이름·`DEVQ_API_MONTHLY_CAP_USD`·`DEVQ_API_MIN_REMAINING_USD`·`JUDGE_MAX_BUDGET_USD`·`API_CLOSE_STATUSES`·`API_CLOSE_WORDS`·`API_KEY_ENV_NAMES` |
| 〃 | 609 `test_env` | 반환 env에서 키 이름 3개 제외(대소문자 무시) |
| 〃 | 1415~1591 (새) | `api_runs_root`·`kst_now`·`kst_month`·`is_usd`·`read_route_config`(1433)·`sdk_available`(1453)·`read_spend_entries`(1461)·`month_spend`(1484)·`pick_route`(1502)·`envelope_cost`(1531)·`fallback_decision`(1548)·`judge_routes`(1572) |
| 〃 | 2032 `cmd_pick_route` · 2041 `cmd_api_spend_record` · 2063 `cmd_route_fallback` (새) | 하위 명령 3개 |
| 〃 | 2255·2266 `cmd_write_result` | result.json에 `judge_routes` 추가, LATEST.json에도 같은 값 추가(기존 필드 불변) |
| 〃 | 2540~2550 `build_parser` | `pick-route`·`api-spend-record`·`route-fallback` 등록 |
| 〃 | 바꾸지 않음 | `parse_judge_envelope`(1356)·`builder_envelope_summary`(1404)·보호 경로·CLI 필수 플래그·시간 상수·재시도 |
| tools/dev_pipeline/sdk_agent.py (새, LF·ASCII, 237줄) | 54 `take_key` · 109 `result_envelope` · 100 `error_envelope` · 134 `build_options` · 152 `run_query` · 167 `bad_arguments` · 180 `build_envelope` · 220 `main` | SDK로 Judge 1번 실행, envelope 쓰기 |
| tools/dev-run.ps1 (ASCII·CRLF 유지) | 26~30 | 시작 직후 자기 프로세스 환경에서 키 이름 3개 삭제 |
| 〃 | 72 | `$sdkAgent` 경로 |
| 〃 | 124 `Start-Captured` | 선택 인자 `ExtraEnv`(그 자식의 `$psi.EnvironmentVariables`에만, 빈 값은 넣지 않음) |
| 〃 | 140 `Invoke-Captured` · 146 `Wait-Captured`(새) | 기다림·시간 초과 종료 코드를 `Wait-Captured`로 옮김(내용 동일) — 키 해시를 띄운 직후 지우기 위해 |
| 〃 | 369 `Get-JudgePromptText`(새) · 379 `Start-Judge`(경로 고르기) · 407 `Start-JudgeSubscription`(지금 명령 그대로 옮김) · 425 `Start-JudgeApi`(새) | Judge 경로 |
| 〃 | 바꾸지 않음 | `Start-Builder`·`Invoke-Pipeline`·`Invoke-FixPass`·기록 대조·잠금·main 블록 |
| tools/dev_pipeline/requirements-sdk.txt (새, LF) | 5 | `claude-agent-sdk==0.2.188` (PyPI 2026-11-25 KST 확인, 2026-11-23 공개 최신판) |
| tools/dev_pipeline/README.md (CRLF 유지) | 86 · 92~100 | Judge 줄에 안내 1구 · 'Judge 경로 (devq-api 1단계)' 절 7줄 |
| docs/claude/devq-api-route.json (새, LF) | 1 | `{"judge_enabled": false, "approved_ref": "", "approved_kst": ""}` |
| manage-us-stock-strategy/tests/test_dev_pipeline_api_route.py (새, LF, 1016줄) | — | 시험 47개 ((c) 참고) |

## (b) 규칙 요약

```
Judge 1번 시작
   ↓
devpipe pick-route --role judge --key-present yes|no   (한 줄, 파일 안 씀)
   ↓ api 조건 전부 맞음?
   ├─ 아니오 → ROUTE subscription reason=… → 지금 claude -p 그대로
   ↓ 예 (ROUTE api reason=ok budget=…)
api-spend-record reserve (장부에 budget 먼저 적음; 실패 → 구독)
   ↓
sdk_agent.py (키는 이 자식에게만) → judge-N.json(route "api")
   ↓ 시간 초과면 TIMEOUT으로 끝(reserve가 남아 계속 셈)
api-spend-record actual (envelope total_cost_usd; 없으면 안 씀)
   ↓
route-fallback: is_error이고 턴 ≤ 1?
   ├─ 아니오 → 이 envelope 그대로 parse-judge (지금처럼)
   ↓ 예
judge-N.api.json으로 보관 (+인증·잔액·한도류면 그달 닫힘 파일)
   ↓
같은 attempt를 claude -p로 1번 (재시도 횟수 불변)
```

- 경로 고르기(`pick_route`, devpipe.py:1502): Builder 역할은 늘 `builder_stage1`. Judge는 ① `git show HEAD:docs/claude/devq-api-route.json`(작업 트리 아님)이 정확히 세 키를 가진 객체이고 `judge_enabled`가 bool `true`, `approved_ref`·`approved_kst`가 지시문 정규식과 완전 일치(아니면 `disabled`/`config_invalid` — 파일이 HEAD에 없으면 `disabled`, 키가 더 있으면 `config_invalid`라 문서로 금액을 올릴 수 없음) ② `_api-route-off` 없음(`off_file`) ③ `_api-closed-<KST YYYY-MM>` 없음(`closed_month`) ④ `--key-present yes`(`no_key`, devpipe는 값을 안 봄) ⑤ `importlib.util.find_spec("claude_agent_sdk")`(`no_sdk`, import는 sdk_agent에서만) ⑥ 장부상 이번 달 남은 금액 = `DEVQ_API_MONTHLY_CAP_USD` − 사용 ≥ `DEVQ_API_MIN_REMAINING_USD`(아니면 `cap`). budget = min(`JUDGE_MAX_BUDGET_USD`, 남은 금액), 센트 아래 버림. devpipe가 실패하거나 줄이 형식과 다르면 dev-run은 `pick_route_failed`로 구독.
- 장부(`_api-spend.jsonl`, `api-spend-record`만 씀, 덧붙이기만): `{"kst","id","attempt","kind","usd"}`. reserve 1개마다 칸 1개, 같은 (id, attempt)의 다음 actual이 그 칸을 닫음 → 닫힌 칸은 actual, 열린 칸(시간 초과 등)은 reserve로 셈. 칸의 달 = reserve의 KST 달. 줄 하나라도 못 읽으면(JSON 아님·음수·NaN·시간대 없는 kst·폴더) `cap`(fail closed). run 폴더 기록 파일(`Save-Records`·`Test-Records` 대상)은 늘지 않음.
- 넘기기(`fallback_decision`, devpipe.py:1548): route가 `api`인 envelope만. `is_error`가 `true`이고 `num_turns` ≤ 1이면 yes(상태·문구 무관). `error_max_budget_usd`·2턴 이상·`is_error` 아님·턴 수 모름·envelope 없음은 no. yes이면서 `api_error_status` 401·403·429, 또는 400이면서 result·subtype에 `credit`·`limit`(대소문자 무시)이면 `_api-closed-<그 KST 달>`(내용: kst·id·attempt·상태 코드만).
- 결과 표시: result.json과 LATEST.json의 `judge_routes` = `[{attempt, route: api|subscription|fallback}]`(`.api.json`이 있으면 fallback, judge-N.json의 route가 api면 api, 그 밖 subscription). 지시문은 result.json만 적었으나 연결표의 메울 변경(결과 모음 예약이 LATEST.json을 읽음)이 tools/ 재수정 없이 되도록 LATEST.json에도 같은 값을 넣었다.
- log.txt: `ROUTE judge-<n> api reason=ok budget=…` · `ROUTE judge-<n> subscription reason=…` · `ROUTE_FALLBACK judge-<n> reason=…` · `JUDGE start/end attempt=<n> route=api …`.
- 키: dev-run.ps1 시작 직후 `INVESTV2_DEVQ_API_KEY`·`INVESTV2_ANTHROPIC_API_KEY`·`ANTHROPIC_API_KEY`를 `[Environment]::SetEnvironmentVariable(…, $null, 'Process')`로 지움. 사용자 범위 키는 `Start-Judge`에서 있음/없음만(`IsNullOrEmpty` 안), 값은 `Start-JudgeApi` 안 해시에만 담아 그 `ProcessStartInfo`에 넣고 시작 직후 `Clear()`·`$null`(`$env:`·cmd `set` 없음). sdk_agent는 `main` 첫 줄에서 그 키와 `ANTHROPIC_API_KEY`·`ANTHROPIC_AUTH_TOKEN`·`ANTHROPIC_BASE_URL`·`ANTHROPIC_CUSTOM_HEADERS`·`ANTHROPIC_PROFILE`·`INVESTV2_ANTHROPIC_API_KEY`를 `os.environ`에서 꺼내 지우고 CLI에는 `env={"ANTHROPIC_API_KEY": 값}`만. envelope 문자열 안에 키가 보이면 `[redacted]`로 바꿈(방어). 예외는 종류 이름·HTTP 상태만.
- 지시문 밖에서 정한 작은 것(모두 허용 파일 안): sdk_agent 인자 검사(프롬프트 한 줄·ASCII, 턴 범위, budget이 0 초과 `MAX_BUDGET_USD` 이하 — devpipe 상수와 같음을 시험이 지킴) → 어긋나면 SDK를 부르지 않는 오류 envelope(턴 0 → 넘기기). `is_error`가 bool이 아니면 오류로 씀(parse-judge가 성공으로 읽지 않게). 결과 없이 예외로 끝나면 `num_turns` = 받은 assistant 메시지 수(작업 뒤 실패를 다시 띄우지 않는 쪽으로 보수적). sdk_agent 표준 출력·오류는 `judge-N.api.out`·`judge-N.api.err`(넘긴 뒤 구독 Judge의 `judge-N.err`와 겹치지 않게). 넘긴 구독 Judge는 지금 명령 그대로라 시간 상한도 그대로 한 번 더 받는다(작업 전 실패는 보통 몇 초).
- 한계: CLI가 잔액 부족을 HTTP 상태 없이 알리면 넘기기는 되지만 그달 닫힘은 안 생김(지시문 조건: 400일 때만 문구 대조) → 매 run이 API를 먼저 시도하고 몇 초 뒤 구독으로 넘어감. 시간 초과된 api Judge는 envelope이 없어 `judge_routes`에 그 attempt가 빠지고 log의 `ROUTE` 줄과 장부 reserve로만 남는다.

## (c) 시험

시험 이름(새 파일 47개): PickRouteTests(조건 표 18가지 — HEAD 꺼짐·작업 트리만 켜짐·approved_ref 형식/다른 사용자·approved_kst 형식·키 추가·bool 아님·JSON 아님·끄기 파일·그달 닫힘·key-present no·SDK 없음(find_spec 가짜)·남은 금액 미달·장부 못 읽음/음수/시간대 없음/폴더·builder 역할, HEAD에 파일 없음, HEAD 켜짐이 작업 트리 꺼짐을 이김, budget = 남은 금액, 상수, 저장소 스위치 꺼짐) · MonthBoundaryTests(UTC 11-30 16:00 = KST 12-01, 새 달에 사용·닫힘 초기화, 장부 kst를 KST 달로) · LedgerTests(reserve만/actual 대체/같은 id 재사용/시간 초과 뒤, 기록 명령, 구독 envelope·잘못된 값 거절) · RouteFallbackTests(턴 0 → yes, 401 → yes+닫힘, 400+credit/limit → 닫힘, 400·500·529·없음 → 닫지 않음, 403·429 → 닫힘, 3턴·max_budget(5턴/1턴)·정상·턴 모름·api 아님·envelope 없음 → no, 닫힘 달 KST) · JudgeRoutesTests(write-result `judge_routes`, 기존 키 불변, LATEST.json) · TestEnvTests(세 이름 없음) · SdkAgentTests(가짜 `claude_agent_sdk`로 옵션 값 전부, env에 ANTHROPIC_API_KEY만, envelope 키 ⊇ `claude -p` 키·`parse_judge_envelope` PASS, 키 없음 → SDK 안 부름, 작업 전/뒤 예외, 오류 결과 뒤 종료 예외, bool 아닌 is_error, 키 가림, 인자 오류, SDK import 실패, 키가 envelope·stdout·장부·route 줄·닫힘 파일에 없음, 새 python 프로세스로 끝까지 — 일곱 이름이 프로세스 환경에 없음) · DevRunStaticTests(키 삭제 위치, 키 읽기 2곳, ExtraEnv 1곳, 로그 줄에 키 없음, 순서, 구독 명령 상수, ROUTE 정규식 ↔ devpipe 출력, Wait-Captured) · StartJudgeCopyTests(dev-run.ps1의 main 앞 정의만 복사해 가짜 devpipe·sdk_agent·claude로 실행 — 사용자 범위 키 읽기는 사본에서 가짜 값으로 바꿈: 구독/api/넘기기/장부 실패/pick-route 실패/키 없음, 키가 sdk 자식에만 가고 devpipe·claude·로그에 없음) · RequirementsTests(판 고정, SDK import는 sdk_agent만).

```
python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline_api_route.py"
----------------------------------------------------------------------
Ran 47 tests in 37.431s

OK
```

```
python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"
----------------------------------------------------------------------
Ran 162 tests in 176.605s

OK
```

(전체 스위트는 지시문대로 돌리지 않음. 추가로 tools/*.ps1 6개를 PowerShell 파서로만 읽어 구문 오류 0 확인 — 실행 없음. 이 세션의 Bash·PowerShell 규칙이 그 스크립트 이름이 든 명령을 막으므로 폴더 단위로 읽었다.)

`git diff --stat` (추적 파일만; 새 파일 5개는 미추적이라 빠짐 — 아래 목록):

```
 tools/dev-run.ps1             |  83 ++++++++++++-
 tools/dev_pipeline/README.md  |  12 +-
 tools/dev_pipeline/devpipe.py | 276 +++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 366 insertions(+), 5 deletions(-)
```

`git diff --ignore-cr-at-eol --stat`: 위와 같음(줄바꿈 변환 없음).

새 파일(미추적): tools/dev_pipeline/sdk_agent.py 237줄 · tools/dev_pipeline/requirements-sdk.txt 5줄 · docs/claude/devq-api-route.json 1줄 · manage-us-stock-strategy/tests/test_dev_pipeline_api_route.py 1016줄 · docs/claude/devq-api-report.md(이 파일).

## (d) 지금 Judge 명령 ↔ SDK 옵션

근거: claude-agent-sdk-python 태그 v0.2.188의 `types.py`(ClaudeAgentOptions·ResultMessage)·`_internal/transport/subprocess_cli.py`(`_build_command`·`connect`)·`_errors.py`(ResultError), 2026-11-25 KST 읽음.

| 지금 `claude -p` (Start-JudgeSubscription) | sdk_agent `ClaudeAgentOptions` | SDK가 CLI에 넘기는 것 | 같음/다름 |
|---|---|---|---|
| run.json `claude_exe` | `cli_path=--cli`(같은 값) | 그 exe | 같음. SDK는 Windows에서 .cmd/.bat을 거절 — 이 PC는 `claude.exe` |
| `-p "<프롬프트 한 줄>"` | `query(prompt=…)` | `--input-format stream-json`(표준 입력으로 프롬프트) | 전달 방식만 다름(SDK 고정) |
| `--model opus` | `model="opus"` | `--model opus` | 같음 |
| `--effort xhigh` | `effort="xhigh"` | `--effort xhigh` | 같음 |
| `--tools "Read,Grep,Glob"` | `tools=["Read","Grep","Glob"]` | `--tools Read,Grep,Glob` | 같음 |
| `--permission-prompts none` | `extra_args={"permission-prompts":"none"}` | `--permission-prompts none` | 같음(명시 안 하면 CLI 기본 `host`) |
| `--strict-mcp-config` | `strict_mcp_config=True` | `--strict-mcp-config` | 같음 |
| `--setting-sources project` | `setting_sources=["project"]` | `--setting-sources=project` | 같음(= 형식) |
| `--disallowedTools "mcp__*"` | `disallowed_tools=["mcp__*"]` | `--disallowedTools mcp__*` | 같음 |
| `--max-turns $JudgeMaxTurns` | `max_turns=--max-turns`(같은 상수) | `--max-turns …` | 같음 |
| (기본 시스템 프롬프트) | `system_prompt={"type":"preset","preset":"claude_code"}` | 플래그 없음 → CLI 기본 | 같음. SDK 기본값(None)은 `--system-prompt ""`라서 명시 |
| 작업 폴더 = worktree | `cwd=--cwd`(worktree) | CLI 자식의 작업 폴더 | 같음. python(sdk_agent) 자신은 devpipe처럼 메인 체크아웃에서 돈다 |
| 45분, 넘으면 프로세스 트리 종료 | — | — | 같음(`Wait-Captured`, cmd → python → claude 트리) |
| `--output-format json` → judge-N.json | 마지막 `ResultMessage` → sdk_agent가 같은 키로 judge-N.json | `--output-format stream-json --verbose` | 다름(SDK 고정). parse-judge가 읽는 키는 같고 `route`·`api_error_status`·`kst_end`만 더함 |
| (없음) | `max_budget_usd=--budget` | `--max-budget-usd …` | 추가(제안서 ②: 한 번 넘침 최대 = 남은 금액 이하) |
| 물려받은 환경 | 일곱 이름을 지운 환경 + `env={"ANTHROPIC_API_KEY": 키}` | SDK가 `CLAUDE_CODE_ENTRYPOINT=sdk-py`·`CLAUDE_AGENT_SDK_VERSION`을 더함 | 다름(의도: 키는 CLI에만) |

실제 `claude -p` Judge envelope(메인의 최근 judge-1.json 3개, 키 이름만 확인)에도 `api_error_status`가 있다. sdk_agent envelope은 그중 파이프라인이 읽는 10개 키(`type`·`subtype`·`is_error`·`result`·`num_turns`·`total_cost_usd`·`usage`·`modelUsage`·`session_id`·`duration_ms`)에 3개를 더한 것이다.

## (e) 플래그 탐침

- 확인한 것(모델 호출 없음, 2026-11-25 KST, 이 PC `claude` 2.1.317 = `%USERPROFILE%\.local\bin\claude.exe`): `--help`에 `--input-format`(선택: text·stream-json), `--permission-prompts`(선택: host·none, 기본 host), `--max-budget-usd`, `--effort`(xhigh 포함) 있음. 기존 `probe_hidden_flag`(devpipe.py:564)와 같은 방식으로 SDK가 만드는 플래그 전부 + `--zz-devpipe-probe -p`를 넣으면 `error: unknown option '--zz-devpipe-probe'`로 끝남. 대조: `--permission-prompts bogus`·`--input-format bogus`는 알 수 없는 플래그보다 먼저 "Allowed choices"로 거절 → 앞쪽 플래그와 선택값이 파서에서 차례로 검증됨. 즉 지금 CLI 파서는 SDK 방식 플래그 묶음을 받는다.
- 판단: preflight는 바꾸지 않았다. `--permission-prompts none`은 이미 preflight 필수 플래그다(devpipe.py:38~52 `REQUIRED_CLI_FLAGS`, help로 확인). `--input-format stream-json` 등 SDK 전용 플래그를 preflight 필수로 넣으면 CLI가 바뀔 때 구독 run까지 멈춘다(안전은 그대로, 가용성만 나빠짐). 대신 CLI가 SDK 플래그를 거절하면 작업 전 실패(턴 0)라 route-fallback이 같은 attempt를 구독으로 돌린다 — api 경로가 스스로 물러난다. 기존 preflight 판정은 약해지지 않았다.
- 확인 필요(첫 켜기 전, 사장실): ① 설치된 SDK 0.2.188이 실제로 띄운 CLI가 stream-json 입력과 위 플래그 묶음으로 끝까지 도는지(여기서는 SDK 미설치·호출 금지라 파서까지만 확인) ② SDK로 띄운 CLI 사용분이 API 크레딧에서 빠지는지(제안서 1-2절 Console 확인, 문서에 없음) ③ run.json `claude_exe`가 앞으로도 `.exe`인지(.cmd면 SDK 거절 → 늘 넘기기).

## (f) 병합 뒤 사장 손

1. 설치 1줄(사장 PowerShell): `pip install -r tools\dev_pipeline\requirements-sdk.txt`
2. Console 선행 조건(읽기·설정은 사장): Billing 자동 충전 꺼짐 · 구매 크레딧 없음 확인 · 'API credit (Max)' 잔액 기록 · 실행기 workspace 안에 개발 큐 전용 키를 만들어 사용자 변수 `INVESTV2_DEVQ_API_KEY`로 둠(이 세션은 만들거나 읽지 않음).
3. 켜기: 별도 켜기 카드 → `docs/claude/devq-api-route.json`을 `judge_enabled: true`와 그 카드의 `approved_ref`(`card cmsg_… option … by user_01KuMGKfZu1SBYxtMmg4vAiH`)·`approved_kst`(`YYYY-MM-DD HH:MM:SS KST`)로 바꿔 커밋(HEAD 커밋본만 읽힘). 첫 api Judge 뒤 제안서 1-2절대로 Console 대조.
4. 즉시 끄기 1줄(다음 run부터 구독, 커밋 없음): `New-Item -ItemType File workspace\outputs\dev-runs\_api-route-off`

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| `docs/claude/devq-api-route.json` HEAD본 · `_api-spend.jsonl` · 끄기/닫힘 파일 · judge-N.json `route` | Windows 작업 InvestmentV2-DevQueue → tools/dev-run.ps1 `Start-Judge`(379) | devpipe `pick_route`(devpipe.py:1502, 명령 2032) · `fallback_decision`(1548, 명령 2063) · 장부 `month_spend`(1484) | Judge가 `Start-JudgeApi`(dev-run.ps1:425) 또는 `Start-JudgeSubscription`(407)으로 뜸, 작업 전 실패면 구독으로 1번 더 | 끊김 — result.json·LATEST.json `judge_routes`(devpipe.py:2255·2266)를 자동으로 읽는 예약 없음. 메울 변경: 사장실 결과 모음 예약이 dev-runs LATEST.json의 `judge_routes`를 읽게 하기(지침 4절 `예약 작업 변경 승인: <이름>`, 이 작업 밖). 그 전까지 사장실이 켠 뒤 첫 run을 직접 읽음(제안서 1-2절) | 연결(경로) · 알림 끊김 |
