# 개발 큐 Judge를 API 크레딧 경로로 — 수정안 (devq-api-1125, ② 구현)

- 상태: 수정안 2판(조언 반영). 사장 카드(당일 1회) 전. tools/ 변경이라 수동 경로(worktree Builder → 별도 읽기 전용 Judge → 사장 PowerShell 병합).
- 근거 결정: api-credit-expand-1125(2026-11-25 09:18:26 KST 카드 A "P1b 개발 큐 + P2 시범", 설계 2·8절).
- 부딪히는 결정·규칙: CLAUDE.md Session hygiene "Manual route … tools/**"·Change classes "Authority/limit change"(카드 승인 4가지 기록) · 지침 1절(비밀 읽기 금지) · 기억 api-credits-max-1106(`ANTHROPIC_API_KEY`를 사용자 변수로 두지 않음). 새 권한·주문·한도 변경 없음.
- 읽은 원문(2026-11-25 09:2x~10:0x KST, 회사PC HEAD 4edb16c): tools/dev-run.ps1(sha256 f2b4548b…) 26~49·115~135·324~364·395~525행 · tools/dev_pipeline/devpipe.py(sha256 0dfeec1c…) 36~57·104~120·584~592·1333~1386·1512행 · run_llm_pilots.ps1 56~61행 · llm_pilot_common.py 18·27·50~54행 · workspace/outputs/dev-runs/*/builder-*.json·judge-*.json · platform.claude.com/docs/en/about-claude/api-credits-for-subscribers(11/25) · claude-agent-sdk-python ClaudeAgentOptions·ResultMessage(Context7, 11/25).

## 0. 결론
1. **1단계는 Judge만 API로 옮긴다.** Judge는 도구가 Read·Grep·Glob뿐(dev-run.ps1 356행)이라 시험 코드·셸이 돌지 않아 키가 샐 길이 없다. 11월 Judge만 34회 $48.54(정가 환산) → 월 약 $58어치가 구독에서 빠진다.
2. **Builder는 2단계로 미룬다.** Builder는 자기가 쓴 시험을 돌리고, devpipe `test_env`(584~588행)가 환경 변수를 통째로 물려준다. 같은 PC·같은 계정에서 키를 완전히 숨길 방법을 실제 탐침으로 증명한 뒤 별도 카드로 켠다.
3. **상한까지만 API, 넘거나 실패하면 지금처럼 구독.** 크레딧이 떨어지면 API 요청은 멈추고 구독으로 넘어가지 않는다(공식 문서) → 자동으로 구독으로 돌아가는 장치가 있어야 큐가 서지 않는다. 기다림은 늘지 않는다(같은 claude.exe를 SDK가 띄움).
4. **경로는 Agent SDK(Python).** 공식 표: Agent SDK = 크레딧 대상, Claude Code = 대상 아님. SDK가 띄운 CLI 사용분이 실제로 크레딧에서 빠지는지는 문서에 없다 → **첫 1건으로 Console에서 확인**(1-2절). 안 빠지면 끈다.

## 1. 1건 비용
### 1-1. 지금까지(정가 환산 `total_cost_usd`, 청구액 아님)
| 항목 | 값 |
|---|---|
| run 1건(Builder+Judge) 중앙값 / 평균 / 최대 | $2.48 / $3.49 / $12.73 (73건) |
| Judge 1번 중앙값 / 평균 / 최대 | $1.26 / $1.42 / $3.77 (72번), 걸린 시간 중앙값 210초 |
| 2026-11(1~25일) | run 29건 $98.08 · 그중 Judge 34번 $48.54 |
재는 법: `workspace/outputs/dev-runs/<id>/judge-N.json`(·builder-N.json)의 `total_cost_usd`.

### 1-2. 켜기 전·첫 1건 확인(사장 손 = Console 읽기만)
- 켜기 전(선행 조건): Billing에서 자동 충전 꺼짐 · 구매 크레딧 0 · 'API credit (Max)' 잔액 기록.
- 첫 API Judge 1번이 끝나면 이 프로젝트가 envelope(`route:"api"`·`total_cost_usd`·`duration_ms`)를 보고하고, 사장이 Console Usage에서 **개발 큐 전용 키**(2절 ⑤)의 그날 사용량과 크레딧 잔액을 본다.
  - 크레딧이 그만큼 줄었다 → 유지. 구매 크레딧·카드에서 나갔거나 'Credit balance too low'로 멈췄다 → 끄기(2절 ⑥).
  - `duration_ms`가 구독 Judge 중앙값(210초)보다 뚜렷이 길면(2배 넘음) 끈다(사장 조건 "기다림 안 늘림").
- 2주 뒤 장부 합과 Console 청구액을 대조해 상한을 다시 잡는다(사장 카드).

## 2. 수정안 (수동 경로 Builder가 만들 것)
허용 파일: `tools/dev-run.ps1` · `tools/dev_pipeline/devpipe.py` · 새 `tools/dev_pipeline/sdk_agent.py` · 새 `tools/dev_pipeline/requirements-sdk.txt` · `tools/dev_pipeline/README.md` · 새 `docs/claude/devq-api-route.json` · 시험 새 `manage-us-stock-strategy/tests/test_dev_pipeline_api_route.py`(이름이 `test_dev_pipeline*`라 보호 대상 — devpipe.py 118행).

① **경로 고르기는 devpipe**(dev-run.ps1은 띄우기만): 새 하위 명령 `pick-route --run-dir --role judge` → `ROUTE api|subscription reason=…`. `api` 조건 전부:
   - `docs/claude/devq-api-route.json`의 **git HEAD 커밋본**이 `judge_enabled:true`이고 approved_ref 형식(`card cmsg_… option … by user_01KuMGKfZu1SBYxtMmg4vAiH`)·approved_kst가 맞음(llm-pilots-schedule.json과 같은 방식, 내용은 켜기 여부와 승인 기록뿐).
   - 끄기 파일 `workspace/outputs/dev-runs/_api-route-off`(추적 안 함)이 없음. 이번 달 닫힘 표시 `_api-closed-<YYYY-MM>`(추적 안 함)이 없음.
   - SDK import 가능 · 개발 큐 전용 키 '있음'(값은 안 봄).
   - 장부상 이번 달(KST) 남은 금액 ≥ $3. 상한은 **코드 상수** `DEVQ_API_MONTHLY_CAP_USD = 60`(docs 파일로 올릴 수 없음).
   - 하나라도 아니면 `subscription`(지금 `claude -p` 그대로). 이유를 log.txt에 남김. `role builder`는 1단계에서 늘 `subscription`.
② **장부**: `workspace/outputs/dev-runs/_api-spend.jsonl`(추적 안 함, 덧붙이기만). 띄우기 전에 `{kst, id, attempt, reserve_usd}`, 끝나면 `{…, actual_usd}`. 합계는 actual이 있으면 actual, 없으면(시간 초과로 envelope 없음 — dev-run.ps1 131~134행) reserve로 센다. `max_budget_usd = min(8, 남은 금액)`.
③ **`sdk_agent.py`**: 지금 Judge 명령(356행)과 같은 값을 `ClaudeAgentOptions`로: `cli_path` = run.json `claude_exe` · `system_prompt={"type":"preset","preset":"claude_code"}`(명시) · `model="opus"`·`effort="xhigh"`·`tools=["Read","Grep","Glob"]`·`disallowed_tools=["mcp__*"]`·`max_turns` = JudgeMaxTurns · `strict_mcp_config=True` · `setting_sources=["project"]` · `extra_args={"permission-prompts":"none"}` · `cwd` = worktree. 결과 `ResultMessage`를 지금 `--output-format json`과 같은 키(`type`·`subtype`·`is_error`·`result`·`num_turns`·`total_cost_usd`·`usage`·`modelUsage`·`session_id`·`duration_ms`)에 `route:"api"`·`api_error_status`·`kst_end`를 더해 `judge-N.json`에 쓴다. **parse_judge_envelope(1333~1375행)은 고치지 않는다.**
   - 병합 전 확인(모델 호출 없이): SDK 방식으로 띄운 CLI가 `--permission-prompts none`을 받는지 기존 플래그 탐침(devpipe.py 53~57행)처럼 확인. 안 되면 BLOCKED.
④ **실패 넘기기**(판정은 devpipe 새 하위 명령 `route-fallback`): API envelope이 `is_error`이고 `num_turns ≤ 1`(작업 전 실패)이면 상태 코드·문구와 무관하게 같은 attempt를 `claude -p`로 1번 다시 띄운다. 사유가 인증·잔액·한도류(401·403·429·400+`credit`·`limit` 대소문자 무시)면 `_api-closed-<달>`을 만들어 그달 나머지는 subscription. `num_turns ≥ 2`의 실패·`error_max_budget_usd`는 지금처럼 JUDGE_ERROR로 끝낸다(이중 비용 방지, 재시도 횟수 불변).
⑤ **키**: 개발 큐 **전용 키**를 새 사용자 변수 `INVESTV2_DEVQ_API_KEY`로 둔다(같은 실행기 workspace 안에서 만든 키 — Console에서 키별 사용량, 이것만 폐기 가능). dev-run.ps1은 시작 때 자기 환경에서 `INVESTV2_ANTHROPIC_API_KEY`·`INVESTV2_DEVQ_API_KEY`·`ANTHROPIC_API_KEY`를 지우고, sdk_agent를 띄우는 그 프로세스에만 `$psi.EnvironmentVariables`로 넣는다(`$env:`·cmd `set` 금지). sdk_agent는 읽은 즉시 자기 환경에서 지우고 CLI에는 `env={"ANTHROPIC_API_KEY": 값}`만 넘기며 `ANTHROPIC_AUTH_TOKEN`·`ANTHROPIC_BASE_URL`·`ANTHROPIC_CUSTOM_HEADERS`·`ANTHROPIC_PROFILE`은 지운다. devpipe `test_env`도 세 이름을 뺀다(구독 경로 Builder 시험이 지금 볼 수 있는 길도 닫힘). 키 값·일부 글자를 어디에도 쓰지 않는다.
   - 한계(숨기지 않음): 같은 Windows 계정의 의도적 읽기(사용자 변수 저장소)는 막지 못한다. 방어선은 전용 키 · workspace 한도 $95 · 자동 충전 꺼짐이다.
⑥ **끄기**: 즉시 = 사장 PowerShell 1줄로 `_api-route-off` 만들기(커밋 없음, 다음 run부터 subscription). 정식 = devq-api-route.json `judge_enabled:false` 커밋(카드). 키 폐기는 전용 키만.
⑦ **의존성**: `requirements-sdk.txt`에 `claude-agent-sdk==<Builder가 PyPI에서 고정한 판>`. 설치는 병합 뒤 사장 PowerShell 1줄. 없으면 ①에서 subscription.
⑧ **시험**(가짜 SDK·가짜 키): 경로 표(꺼짐·끄기 파일·닫힘 표시·키 없음·SDK 없음·남은 금액 < $3·월 경계 KST·HEAD와 작업 트리 다름·builder 역할 → subscription), 장부 reserve/actual 합산, max_budget 계산, envelope 키 동일성(parse_judge_envelope 무수정 통과), 넘기기 조건, test_env에서 세 이름 빠짐, 가짜 키 문자열이 모든 출력에 없음. dev-run.ps1은 ASCII 유지.

## 3. 2단계(Builder) — 이번 카드에 들지 않음
- 조건: 실제 키로 도는 탐침 run 1번이 Builder의 Bash·PowerShell·unittest 자식 프로세스에서 키 이름 셋 '없음'을 기록. 1차 worktree가 이미 있을 때 다시 띄우는 법(fix pass처럼 `--worktree` 없이)과 `error_max_budget_usd` 멈춤 상태를 함께 만든다. 별도 수정안·카드.

## 4. 연결표 (지침 8절 · analysis-linkage-map 1절 8번)
| 칸 | 내용 | 상태 |
|---|---|---|
| ① 자료 | `devq-api-route.json` 커밋본 · `_api-spend.jsonl` · 끄기·닫힘 표시 | 끊김 — 이 수정안 병합으로 생김 |
| ② 읽는 점검 | devpipe `pick-route`·`route-fallback`(새, 병합 뒤 행 번호 기록) | 끊김 — 수동 경로 Builder |
| ③ 바뀌는 행동 | dev-run.ps1 Start-Judge(356행)가 api/subscription으로 뜸 | 끊김 — 수동 경로 Builder |
| ④ 소비자 | 개발 큐 run의 Judge 전부 · 비용 보고는 이 프로젝트(1-2) | 연결 |
| ⑤ 끊김 알림 | log.txt `ROUTE …`·`ROUTE_FALLBACK` → result.json에 route 표시(Builder가 devpipe write-result에 추가) → 이 프로젝트가 1-2 때 읽음. 자동으로 읽는 예약 없음 — 메울 변경: 사장실 결과 모음 예약이 dev-runs LATEST.json의 route를 읽게 하기(지침 4절 `예약 작업 변경 승인: <이름>`, 이 작업 밖) | 끊김(알림) |
| 승인 경로 | 코드 = 오늘 카드(수동 경로) → 실행 스레드(사장실 한 줄) → Judge → 사장 PowerShell 병합 · 켜기 = 1-2 선행 조건 뒤 별도 카드 + 커밋 | — |

## 5. 상한 배분 (실행기 workspace 월 $95 — 사장이 Console에서 설정)
| 사용처 | 월 상한 | 근거 |
|---|---|---|
| 개발 큐 Judge(1단계) | $60(코드 상수) | 11월 25일 Judge $48.54 → 월 약 $58 |
| iccheck · news | $10 · $5 | llm_pilot_common.py 27행 |
| pdfcmp · srccheck(P2) | $5 · $6 | 같은 행 |
| 합 | $86(여유 $9) | 한 번 넘침 최대 = 남은 금액 이하(②의 max_budget) |

## 6. 바뀔 조건
- 첫 1건이 크레딧에서 빠지지 않거나 2배 넘게 느리면 → 끔(NO_CHANGE), Claude Code 크레딧 대상 여부가 바뀌면 다시 봄.
- SDK 방식 CLI가 `--permission-prompts none`을 못 받으면 → BLOCKED, 다른 방법 검토.
- 2주 실측에서 API Judge 1번 값이 구독 정가 환산과 ±30% 넘게 다르면 상한 재조정.

검토 기록: 조언(Fable) 8건 — 결론 바뀜 2(키 안전 → Judge만 1단계·Builder 탐침 뒤, '시험으로 증명' 불가 → 실제 탐침) · 정정 6(넘기기 조건 넓힘·그달 닫힘, system_prompt 명시·플래그 탐침, 켜기 파일을 docs/claude로·끄기 파일, 장부 reserve/actual·max_budget=남은 금액·평균 기준, 선행 조건·전용 키·지연 비교, worktree·예산 초과 → 2단계로) · 미반영 0 (작업자 144,971 토큰, 약 4분 45초). 원문 확인: devpipe.py 109~118·584~588행, dev-run.ps1 115~135·485~525행(11/25 재확인).

## 7. 사장 결정 (2026-11-25 09:32:27 KST)
- 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9YEvrpbLTSAKYXCJHcm1KZm · 수정안 devq-api-1125(이 문서 2판, sha256 bbadf4ad…) · 선택지 A '만들기 승인 (Judge만)' · 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH(프로젝트 주인) · 시각 2026-11-25 09:32:27 KST. 이 승인은 이 수정안 하나, 오늘(KST) 1회.
- 다음: 사장실 직접 한 줄로 실행 스레드 시작 → 수동 경로 Builder(worktree) → 별도 읽기 전용 Judge → 사장 PowerShell 병합(꺼진 채). 켜기는 별도 카드.

## 8. 실행·병합 기록 (2026-11-25 KST, 실행 스레드 '개발 큐 검사를 API 크레딧으로 전환')
- 사장 직접 입력 09:54 KST "개발 큐 API 전환 실행해" → Builder(회사PC 세션, worktree magical-chatterjee-dc076d, 시험 47·162 OK) → 별도 읽기 전용 Judge VERDICT: PASS(docs/claude/devq-api-judge-report.md) → 병합 스크립트 docs/claude/devq-api-merge-2026-11-25.ps1.
- llm-pdfcmp 먼저 병합(f184e56) 뒤 사장 PowerShell 병합 16:17 KST 전후: worktree 커밋 aa4b547, main 6ba732a. HEAD의 devq-api-route.json = judge_enabled false(꺼짐 확인).
- 남은 것: 켜기 카드(Console 전용 workspace·전용 키 INVESTV2_DEVQ_API_KEY·자동 충전 꺼짐·잔액 기록, pip install -r tools\dev_pipeline\requirements-sdk.txt, 보고서 (e) 확인 3가지).

## 9. 켜기 (2026-11-25 16:19:52 KST)
- 사장 사장실 직접 입력 16:18:58 KST "개발 큐 API 켜기" → 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9J7iQ3Gd4YnoDV6SGRg1kvs 선택지 A '켜기 승인 (준비 3가지 끝남)' · 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH · 16:19:52 KST.
- docs/claude/devq-api-route.json을 judge_enabled true + approved_ref·approved_kst로 씀(LF), _pending/devq-api-on-2026-11-25.txt. 효력은 docs-commit으로 HEAD에 들어간 뒤부터(pick-route는 HEAD본만 읽음).
- 준비 3가지(Console 전용 키·자동 충전 꺼짐, 사용자 변수, SDK 설치)는 사장 카드 문구로만 확인(스레드는 키를 읽지 않음). 빠졌으면 매 run이 구독(no_key/no_sdk)으로 돈다.
- 다음: 첫 개발 큐 run의 log.txt ROUTE 줄·result.json judge_routes·_api-spend.jsonl과 Console 차감을 대조.
