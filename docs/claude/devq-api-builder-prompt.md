---
id: devq-api-builder-prompt
title: "개발 큐 Judge를 API 크레딧(Agent SDK) 경로로 — 1단계 Judge만 — devq-api Builder"
date: 2026-11-25
class: "K3 수동 경로(tools/ 보호 경로). 회사PC worktree Builder(Opus) → 별도 읽기 전용 Judge → 병합은 사장 PowerShell(꺼진 채)"
source: "docs/claude/devq-api-proposal-2026-11-25.md 2판 2절, 사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9YEvrpbLTSAKYXCJHcm1KZm '만들기 승인 (Judge만)' 2026-11-25 09:32:27 KST, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH"
authority: "권한 표지 4종 줄 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음 · API 키 값을 읽거나 출력하지 않음 · 켜지 않음(judge_enabled false로 병합)"
---

## 목표
개발 큐 Judge(`tools/dev-run.ps1` Start-Judge, 지금 356행 `claude -p … --model opus --effort xhigh --tools "Read,Grep,Glob"`)를, 켜졌을 때만 Agent SDK(Python)로 같은 claude.exe를 띄워 API 크레딧으로 돌린다. 꺼짐·상한·키 없음·SDK 없음·작업 전 실패면 지금과 똑같이 `claude -p`(구독)로 돈다. Builder는 이번에 바꾸지 않는다.

## 바꿀 파일 (이 7개만)
- tools/dev-run.ps1 (기존 — 원래 줄바꿈 유지, ASCII만)
- tools/dev_pipeline/devpipe.py (기존 — 원래 줄바꿈 유지)
- tools/dev_pipeline/sdk_agent.py (새, LF, ASCII)
- tools/dev_pipeline/requirements-sdk.txt (새, LF)
- tools/dev_pipeline/README.md (기존 — 경로 고르기·끄기 파일·장부 몇 줄)
- docs/claude/devq-api-route.json (새, LF) — `{"judge_enabled": false, "approved_ref": "", "approved_kst": ""}`
- manage-us-stock-strategy/tests/test_dev_pipeline_api_route.py (새, LF)
- 보고 docs/claude/devq-api-report.md (새, LF) — 위 7개와 별도로 허용

## 먼저 읽을 것 (고치지 않는 곳 포함)
- docs/claude/devq-api-proposal-2026-11-25.md 전체(특히 2절 ①~⑧).
- tools/dev-run.ps1 전체(115~135 Start-Captured·Invoke-Captured, 324~364 Start-Builder·Start-Judge, 395~525 Invoke-Pipeline).
- tools/dev_pipeline/devpipe.py: 36~57(CLI 플래그 탐침), 104~120(보호 경로), 584~592 `test_env`, 1333~1386 `parse_judge_envelope`·`builder_envelope_summary`, 1804~1828 `cmd_parse_judge`, 1946~2030 `cmd_write_result`, 2240~2290 하위 명령 등록.
- manage-us-stock-strategy/scripts/llm_pilot_common.py 48~56행(지울 환경 변수 목록), manage-us-stock-strategy/scripts/run_llm_pilots.ps1 50~65행(사용자 범위 변수 읽기 방식 — 단 `$env:`에 두는 부분은 따르지 않는다).
- Agent SDK 사실(2026-11-25 Context7, claude-agent-sdk-python): `ClaudeAgentOptions`에 `cli_path`·`system_prompt`·`model`·`effort`·`tools`·`allowed_tools`·`disallowed_tools`·`max_turns`·`max_budget_usd`·`strict_mcp_config`·`setting_sources`·`extra_args`(값 None이면 불리언 플래그)·`env`(물려받은 환경 위에 덮어씀)·`cwd`. `ResultMessage`에 `subtype`·`is_error`·`num_turns`·`session_id`·`duration_ms`·`total_cost_usd`·`usage`·`model_usage`·`result`·`api_error_status`. 고정할 판은 PyPI에서 확인해 requirements-sdk.txt에 `==`로 적고 보고에 판·날짜를 쓴다(확인 못 하면 BLOCKED).

## 구현 요구
1. **devpipe `pick-route --run-dir <d> --role judge|builder`** → 한 줄 `ROUTE api reason=ok budget=<USD>` 또는 `ROUTE subscription reason=<disabled|off_file|closed_month|no_key|no_sdk|cap|builder_stage1|config_invalid>`. `api` 조건(전부): 
   - `git show HEAD:docs/claude/devq-api-route.json`(작업 트리 아님)이 JSON 객체이고 `judge_enabled is True`, `approved_ref`가 정규식 `^card cmsg_[A-Za-z0-9]{20,} option [A-D] by user_01KuMGKfZu1SBYxtMmg4vAiH$`, `approved_kst`가 `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} KST$`. 아니면 disabled 또는 config_invalid.
   - `workspace/outputs/dev-runs/_api-route-off`가 없음, `workspace/outputs/dev-runs/_api-closed-<KST YYYY-MM>`이 없음.
   - SDK: `importlib.util.find_spec("claude_agent_sdk")`가 있음(import는 sdk_agent에서만).
   - 키: dev-run.ps1이 넘긴 인자 `--key-present yes|no`(devpipe는 값을 보지 않는다).
   - 장부 남은 금액 = `DEVQ_API_MONTHLY_CAP_USD`(상수 60) − 이번 달 사용 ≥ `DEVQ_API_MIN_REMAINING_USD`(상수 3). budget = min(`JUDGE_MAX_BUDGET_USD`(상수 8), 남은 금액).
   - `--role builder`는 늘 `subscription reason=builder_stage1`.
   - 고른 결과를 run 폴더 `route-judge-<attempt>.json`에 쓰지 말고(기록 해시 대조에 걸림) log와 아래 장부에만 남긴다. 기존 `Save-Records`·`Test-Records` 대상 파일을 늘리지 않는다.
2. **장부** `workspace/outputs/dev-runs/_api-spend.jsonl`(git 무시 폴더, 덧붙이기만): api로 띄우기 직전 `{"kst":…, "id":…, "attempt":n, "kind":"reserve", "usd":budget}`, 끝난 뒤 `{"…","kind":"actual","usd":total_cost_usd}`. 이번 달 사용 = 각 (id, attempt)에 actual이 있으면 actual, 없으면 reserve. 장부를 못 읽으면 `subscription reason=cap`(fail closed). 새 하위 명령 `api-spend-record --run-dir --attempt --kind reserve|actual --usd`로만 쓴다.
3. **sdk_agent.py** (`python tools/dev_pipeline/sdk_agent.py --role judge --cli <claude_exe> --cwd <worktree> --prompt-file-line "<지금 Judge 프롬프트 한 줄>" --max-turns <n> --budget <usd> --out <judge-N.json>`):
   - 키: 프로세스 환경 `INVESTV2_DEVQ_API_KEY`를 읽자마자 `os.environ`에서 지운다. `ANTHROPIC_API_KEY`·`ANTHROPIC_AUTH_TOKEN`·`ANTHROPIC_BASE_URL`·`ANTHROPIC_CUSTOM_HEADERS`·`ANTHROPIC_PROFILE`·`INVESTV2_ANTHROPIC_API_KEY`도 지운다. CLI에는 `env={"ANTHROPIC_API_KEY": 값}`만 준다. 키가 없으면 SDK를 부르지 않고 `is_error: true, subtype: "no_key", num_turns: 0` envelope를 쓴다.
   - 옵션: `cli_path` = `--cli` · `system_prompt={"type":"preset","preset":"claude_code"}` · `model="opus"` · `effort="xhigh"` · `tools=["Read","Grep","Glob"]` · `disallowed_tools=["mcp__*"]` · `max_turns` · `max_budget_usd` = `--budget` · `strict_mcp_config=True` · `setting_sources=["project"]` · `extra_args={"permission-prompts": "none"}` · `cwd` = `--cwd`. 지금 Judge 명령과 다른 값이 있으면 보고 (d)에 이유를 쓴다.
   - 출력: 마지막 `ResultMessage`를 `{"type":"result","subtype","is_error","result","num_turns","total_cost_usd","usage","modelUsage","session_id","duration_ms","route":"api","api_error_status","kst_end"}`로 `--out`에 UTF-8 JSON으로 쓴다(`modelUsage`는 `model_usage`를 dict로). 예외는 종류 이름과 HTTP 상태만 적은 `is_error: true` envelope로 쓴다(키 값·메시지 원문 금지).
   - 표준 출력에는 한 줄 `SDK-AGENT <role> <ok|error> turns=<n>`만.
4. **dev-run.ps1** (ASCII 유지, 프로세스만 띄움):
   - 시작 직후 자기 프로세스 환경에서 `INVESTV2_DEVQ_API_KEY`·`INVESTV2_ANTHROPIC_API_KEY`·`ANTHROPIC_API_KEY`를 지운다(`Remove-Item Env:…` 또는 `[Environment]::SetEnvironmentVariable(…, $null, 'Process')`). 사용자 범위 `INVESTV2_DEVQ_API_KEY`가 있는지만 확인해 `--key-present`로 넘긴다(값을 변수에 담는 것은 sdk_agent를 띄우는 그 함수 안에서만).
   - Start-Judge: `pick-route` → api면 `api-spend-record reserve` → sdk_agent를 띄우는 **그 ProcessStartInfo에만** `$psi.EnvironmentVariables['INVESTV2_DEVQ_API_KEY']`를 넣는다(`$env:`·cmd `set` 문자열 금지). 이를 위해 Start-Captured에 선택 인자(추가 환경 해시)를 더한다. 끝나면 `api-spend-record actual`(envelope 없으면 건너뜀 → reserve가 남음).
   - **넘기기**: api envelope을 devpipe 새 하위 명령 `route-fallback --run-dir --attempt`가 판정 → `FALLBACK yes reason=…`이면 같은 attempt를 지금 `claude -p` Judge 명령으로 1번 다시 띄운다(envelope 덮어씀, api envelope은 `judge-N.api.json`으로 이름 바꿔 보관). 판정: `is_error`가 참이고 `num_turns ≤ 1`이면 yes(상태 코드·문구 무관). 그때 사유가 인증·잔액·한도류(api_error_status 401·403·429, 또는 400이면서 result·subtype에 `credit`·`limit`(대소문자 무시))면 `_api-closed-<KST YYYY-MM>` 파일을 만든다. `num_turns ≥ 2`의 실패·`error_max_budget_usd`는 no(지금처럼 parse-judge가 처리).
   - log.txt에 `ROUTE judge-<n> api|subscription reason=…`·`ROUTE_FALLBACK judge-<n> reason=…`.
   - Builder 경로(Start-Builder)는 바꾸지 않는다.
5. **devpipe `test_env`**: 반환 env에서 `INVESTV2_DEVQ_API_KEY`·`INVESTV2_ANTHROPIC_API_KEY`·`ANTHROPIC_API_KEY`를 뺀다.
6. **result.json**: `cmd_write_result`가 각 Judge attempt의 route(`api`|`subscription`|`fallback`)를 `judge_routes` 목록으로 더한다(envelope의 `route` 키와 `.api.json` 유무로 판단). 기존 필드는 바꾸지 않는다.
7. **플래그 탐침**(모델 호출 없이): SDK 방식으로 띄운 CLI가 `--permission-prompts none`·`--input-format stream-json`을 받는지, 기존 `probe_hidden_flag` 방식(542~546행)으로 preflight에 확인 항목을 더할지 판단해 보고 (e)에 쓴다. 바꾸면 기존 preflight 판정이 약해지지 않게 한다. 확인이 안 되면 그 사실을 (e)에 '확인 필요'로 적는다(실제 확인은 병합 뒤 첫 켜기 전 사장실이 한다).
8. **바꾸지 않는 것**: `parse_judge_envelope`·`builder_envelope_summary`·Judge 프롬프트·Judge 모델·노력·도구·턴·시간 상수·Builder 명령·재시도 횟수·보호 경로·authority-paths.txt·dev-merge.ps1·dev-queue.ps1.

## 시험 (test_dev_pipeline_api_route.py, 임시 git 저장소·가짜 SDK·가짜 키)
- pick-route 표: HEAD 꺼짐 / 작업 트리만 켜짐(HEAD 꺼짐) / approved_ref 형식 틀림 / 끄기 파일 / 그달 닫힘 파일 / key-present no / SDK 없음(find_spec 가짜) / 남은 금액 < 3 / 장부 못 읽음 / builder 역할 → 모두 subscription과 맞는 reason. 모두 맞으면 api, budget = min(8, 남은 금액).
- 월 경계: KST 기준(UTC 11-30 16:00 = KST 12-01)으로 다른 달.
- 장부: reserve만 있으면 reserve로, actual 있으면 actual로 합산.
- route-fallback: is_error·turns 0 → yes, 401 → yes+닫힘 파일, 400+"credit balance" → 닫힘, turns 3 error → no, error_max_budget_usd turns 5 → no, 정상 → no.
- sdk_agent: 가짜 `claude_agent_sdk` 모듈로 옵션 값 단언(system_prompt preset·tools·disallowed·effort·strict·setting_sources·extra_args·env에 ANTHROPIC_API_KEY만), envelope 키 목록이 지금 `claude -p` envelope 키를 포함, `parse_judge_envelope`가 그 envelope(결과 글 끝 `VERDICT: PASS` + JSON 블록)을 지금처럼 PASS로 읽음.
- 키 미노출: 가짜 키 문자열이 envelope·stdout·장부·log에 없음. sdk_agent 실행 뒤 `os.environ`에 키 이름 6개가 없음. `test_env` 결과에 세 이름 없음.
- Builder 시험 명령(이 글자 그대로): `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline_api_route.py"` 그리고 기존 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`(깨지지 않음 확인). 전체 스위트는 돌리지 않는다.

## 지켜야 할 것
- 허용 파일 밖은 손대지 않는다. `.claude/`·CLAUDE.md·정책·상태 금지.
- 기존 파일 줄바꿈 유지(일괄 변환 금지). dev-run.ps1은 ASCII만.
- 키 값을 읽거나 출력하지 않는다(시험은 가짜 키만). 비밀 파일을 열지 않는다. 사용자 환경 변수를 만들거나 바꾸지 않는다. pip 설치 없음. 실제 API·실제 SDK 호출 없음. dev-run·dev-queue·dev-merge를 실행하지 않는다.
- `docs/claude/devq-api-route.json`은 `judge_enabled: false`로만 만든다.
- git은 status·diff·log만. commit·push·병합 없음.
- 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/devq-api-report.md
(a) 바꾼 함수·줄(파일:행) (b) 경로 고르기·넘기기·장부 규칙 요약 (c) 시험 결과 마지막 3줄과 시험 이름 · `git diff --stat` · `git diff --ignore-cr-at-eol --stat` (d) 지금 Judge 명령과 SDK 옵션 대응표, 다른 값과 이유 (e) 플래그 탐침 판단·확인 필요 (f) 병합 뒤 사장 손: ① `pip install -r tools\dev_pipeline\requirements-sdk.txt` 1줄 ② Console 선행 조건(자동 충전 꺼짐·구매 크레딧 0·잔액 기록·전용 키 `INVESTV2_DEVQ_API_KEY`) ③ 켜기 카드 → devq-api-route.json 커밋 ④ 즉시 끄기 1줄(`New-Item -ItemType File workspace\outputs\dev-runs\_api-route-off`). 수량·금액·키 값·권한 표지 문자열을 적지 않는다('권한 표지 4종 줄 변경 없음').

## 연결표
| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| `docs/claude/devq-api-route.json` HEAD본 · `_api-spend.jsonl` · 끄기/닫힘 파일 · judge-N.json `route` | Windows 작업 InvestmentV2-DevQueue → tools/dev-run.ps1 Start-Judge(지금 356행) | devpipe `pick-route`·`route-fallback`(이 작업이 만듦 — 보고 (a)에 행) | Judge가 api 또는 subscription으로 뜸(지금 356행) | 끊김 — result.json `judge_routes`를 자동으로 읽는 예약 없음. 메울 변경: 사장실 결과 모음 예약이 dev-runs LATEST.json을 읽게 하기 · 승인 경로 지침 4절 `예약 작업 변경 승인: <이름>`(이 작업 밖). 그 전까지 사장실이 켠 뒤 첫 run을 직접 읽음(제안서 1-2절) | 연결(경로) · 알림 끊김 |

조언 생략(이유): 같은 수정안 2판이 Fable 조언(high) 8건을 거쳤고, 이 지시문의 결과는 수동 경로 독립 Judge(Opus xhigh)가 검수한다.
