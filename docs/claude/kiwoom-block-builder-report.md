---
id: kiwoom-block-builder-report
title: "kiwoom-block Builder 보고 — 키움 주문 차단 보강 4건"
date: 2026-10-25
class: "권한(K3) 수동 경로 — 차단만 늘림. 다음: 별도 읽기 전용 Judge(docs/claude/kiwoom-block-judge-prompt.md) → 병합은 사장 PowerShell 한 줄"
base: 7f98f28 (worktree-kiwoom-block, 미커밋)
authority: "order_authority=false · quantity_authority=none · 키움 호출 0건 · 정책·상태·일지·원장 쓰기 0건 · 허용 확대 0건"
consumers: "kiwoom-block Judge · 사장(병합 결정, ① 스위치 확인) · 병합 스크립트 작성자(Cowork/코디네이터)"
---

# 결론
1. **②③④를 만들었다. 새 파일 5개, 기존 파일 수정 0.** `.claude/settings.json`은 그대로 두고, 바꿀 내용은 제안 파일 `docs/claude/kiwoom-block-settings-proposed.json`에 담았다(기존 deny·ask 그대로 + deny 3줄 + `hooks` 절).
2. **deny는 3줄만 넣었다.** `kiwoomcli` 두 줄은 뺐다. 저장소 문서의 Cowork 루틴이 셸에서 `kiwoomcli overseas candles stock-minute`를 직접 부르기 때문이다(manage-us-stock-strategy/references/portfolio-exposure-review.md 259~274행).
3. **④ 결론: 예. 키움 CLI는 해외 주문을 `--confirm`이 있으면 실제로 보낸다.** server.py 271~272행 주석이 틀렸고, CSV(`guarded`)가 맞다. **새로 찾은 것도 있다:** `kiwoom_order_preview`에 `options={"confirm": true}`를 넣으면 `--confirm`이 붙어 실제 주문이 나간다(server.py 142~147행, runner.py 190~202행). 그래서 deny `mcp__*__kiwoom_order_preview`는 중복 방어가 아니라 실제로 필요한 줄이다.
4. **훅이 원격 장치 도구(`mcp__remote-devices__*`)와 Cowork에서 발동하는지는 확인 필요다.** 발동한다고 단정하지 않는다. 훅 명령 형식도 병합 뒤 무해한 시험 한 번으로 확인해야 한다(아래 "병합 뒤 확인").
5. 테스트: 새 테스트 21개 통과. 기준선(`test_dev_pipeline*` 126, `test_approval_human_check*` 28)은 전후 모두 실패 0이다.

# 사장 결정이 필요한 것 (기본값 = 차단 쪽 유지)
- **D1. 훅의 `kiwoomcli` 표지.** 지시문 ③대로 넣었다. 그러면 ②에서 deny를 뺀 이유인 읽기 전용 `kiwoomcli` 호출도 훅이 발동하는 도구에서는 막힌다. Claude Code의 Bash·PowerShell에서는 확실히 막히고, Cowork나 원격 장치에서는 발동 여부가 확인 필요다. 선택지는 (a) 유지(기본, 차단 쪽) 또는 (b) 표지 삭제: 훅 `MARKERS`의 `("kiwoomcli", …)` 한 줄을 지우는 수정이다. 지금 자동 수집(auto-core → collect_30m.ps1)은 Windows 작업 스케줄러에서 돌기 때문에 영향이 없다.
- **D2. `--confirm` 표지가 Cowork의 승인된 apply 경로와 겹친다.** `reconcile_broker_state.py apply --confirm <code> --confirmed-via COWORK_CHAT_USER_MESSAGE`와 `portfolio_review_journal.py apply --confirm <code> …`(broker-snapshot-reconciliation.md 147행, decision-journal-cards.md 38행)가 겹친다. Claude Code에서는 이미 기존 deny가 막는 명령이라 바뀌는 것이 없다. 다만 훅이 Cowork 도구에서도 발동한다면 Cowork의 승인된 apply도 막힌다(확인 필요). 이 경우 사장 본인 터미널(USER_TERMINAL) 경로는 영향이 없다. 기본값은 유지이고, 막히는 것이 확인되면 그때 정한다.

# 파일별 변경
| 파일 | 내용 |
|---|---|
| `.claude/hooks/kiwoom_order_block.py` (새) | PreToolUse 훅. 표준 라이브러리만(json·re·sys), ASCII, CRLF. 거절이면 종료 코드 2와 stderr 한 줄, 아니면 0. 대상: `Bash`·`PowerShell`(`command`), 이름에 `kiwoom`이 든 `mcp__` 도구(입력 전체 + 도구 이름 + confirm 키), 이름이 `device_bash`·`start_process`·`interact_with_process`로 끝나는 `mcp__` 도구(명령 필드 `command`/`cmd`/`input`/`script`만). 파일 쓰기 도구는 대상이 아니다. 깨진 JSON·`tool_name` 없음·`tool_input` 없음·명령 필드 없음·내부 예외는 모두 거절(fail closed). 환경변수·인자·허용 분기는 없다 |
| `docs/claude/kiwoom-block-settings-proposed.json` (새) | 현재 `.claude/settings.json` 바이트를 그대로 둔 채 deny 끝에 3줄과 `hooks` 절만 더했다. ASCII, CRLF |
| `docs/claude/kiwoom-overseas-order-guard-2026-10-25.md` (새) | ④ 결론과 file:line 근거, 주석 제안 문구, 바뀔 조건 |
| `manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py` (새) | 훅 거절·통과·fail closed·파일 형태 테스트와 제안 settings 불변식 테스트(21개) |
| `docs/claude/kiwoom-block-builder-report.md` (새) | 이 보고서 |

## 지시문보다 더 막은 것 (모두 거절만 늘림, 지우기 쉬움)
- `interact_with_process`도 대상에 넣었다. Desktop Commander는 `start_process`로 셸을 연 뒤 `interact_with_process`의 `input`으로 명령을 보낼 수 있어서, 빼면 우회로가 남는다.
- `--confirm` 표지를 `--confirm(?![A-Za-z0-9_-])`로 넓혔다. 지시문의 `(\s|=|$)`가 잡는 경우를 모두 잡고, `--confirm"`·`--confirm;`·`--confirm)`도 잡는다. `--confirmed-via`·`--confirm-…`·`--confirm_…`는 통과한다.
- 8번째 표지 "confirm true"를 더했다(`confirm` 뒤에 `:`/`=`와 `true|1|yes|on`). JSON `"confirm": true`, YAML `confirm: true`, Python `confirm=True`(예: `python -c "… kiwoom_order_submit(…, confirm=True)"`)를 막는다. Judge 항목 4의 `confirm: true` 변형에 맞춘 것이다.
- confirm 키를 MCP 서버와 같은 방식으로 정규화했다(`replace("_","-").lstrip("-")`). 그래서 `confirm`·`-confirm`·`--confirm` 키가 모두 걸리고, 값 `true`·`"true"`·`1`·`"yes"`도 참으로 본다.
- 셸 인용·이스케이프 문자(`" ' ` ^`)를 지운 문자열도 한 번 더 검사한다. `kiwoom"cli`, `kiw^oomcli`, `kiwoom`cli`, `"overseas" "orders"`가 걸린다.
- `hooks` 항목에 `"timeout": 30`, `"onFailure": "block"`을 넣었다. 문서 확인(하위 에이전트가 가져온 code.claude.com/docs/en/hooks.md 요약이라 원문 대조는 확인 필요)에 따르면, 이 설정이 없으면 PreToolUse 훅이 시간 초과되거나 0·2 말고 다른 코드로 끝날 때 도구가 그냥 실행된다(fail open). `onFailure`는 v2.1.295 이상이 필요하다고 하며, 이 PC는 `claude --version` = 2.1.310이다.

# 제안 settings 전후 diff (추가된 줄만)
```
+      "mcp__*__kiwoom_order_preview",
+      "Bash(*overseas orders*)",
+      "PowerShell(*overseas orders*)"
+  "hooks": {
+    "PreToolUse": [
+      {
+        "matcher": "^(Bash|PowerShell|mcp__.*[Kk][Ii][Ww][Oo][Oo][Mm].*|mcp__.*(device_bash|start_process|interact_with_process))$",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/kiwoom_order_block.py\"",
+            "timeout": 30,
+            "onFailure": "block"
+          }
+        ]
+      }
+    ]
+  },
```
기존 마지막 deny 줄 `"Edit(/stock-strategy-system/decision_journal.json)"` 뒤에 쉼표만 붙었다. 다른 줄은 바이트까지 같다(`git diff --no-index`로 확인).

## matcher·command 형식 (일부 확인 필요)
- matcher: 문서 요약에 따르면 글자·숫자·`_`·`-`·공백·`,`·`|` 말고 다른 문자가 있으면 matcher는 앵커 없는 JavaScript 정규식으로 처리된다. 그래서 `^…$`로 묶었다. 테스트는 Python `re`로 fullmatch와 search를 모두 확인한다. `Write`·`Edit`·`Read`·`write_file`은 걸리지 않는다. 괄호 안 교대(`(a|b)`)는 **해소: JS 정규식이라 괄호 안 교대가 된다.** Judge 판단을 인용한다(Judge VERDICT PASS_WITH_FIX, 사장이 스레드에 붙인 수정안 F5, 2026-10-25 12:04:09Z; docs/claude/kiwoom-block-fix1-prompt.md 36행). 근거 출처: code.claude.com/docs/en/hooks.md의 matcher 표 "Contains any other character → JavaScript regular expression, unanchored"와 "tested with JavaScript's `RegExp.prototype.test`"(fix1 Builder가 2026-10-25 WebFetch로 직접 열어 확인). 괄호 묶음 안의 `|` 교대는 JavaScript RegExp 기본 문법이다.
- command 후보 1(채택): `python "${CLAUDE_PROJECT_DIR}/.claude/hooks/kiwoom_order_block.py"`. 문서 요약상 Windows의 훅 명령은 Git Bash로 돌고, `${CLAUDE_PROJECT_DIR}`는 자리표시자이면서 환경변수다. 이 PC에서 `python`은 `C:\Users\…\Python313\python`(3.13.15)이다.
- command 후보 2: 실행 형태 `"command": "python", "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/kiwoom_order_block.py"]`. 문서 요약은 경로 자리표시자가 있을 때 이 형태를 권한다고 한다. 저장소 경로에 `##`와 한글이 있으므로 후보 1이 실패하면 이것으로 바꾼다. 이때 테스트의 `command` 단언도 `args`를 보도록 같이 바꿔야 한다.
- 어느 쪽이든 `onFailure: block` 덕분에 훅이 못 뜨면 대상 도구가 막힌다(fail closed). 반대로 형식이 틀리면 **모든 Bash·PowerShell 호출이 막힌다.** 이때 되돌리는 방법은 사장이 `.claude/settings.json`에서 `hooks` 절을 지우는 것이다.

# 영향 범위 grep (kiwoomcli·kiwoom_cli 사용처)
Grep `kiwoomcli|kiwoom_cli|kiwoom-cli`(대소문자 무시)의 결과는 63개 파일, 131건이다. 셸에서 직접 부르는 곳만 추렸다.
| 위치 | 누가 실행하나 | deny·훅 영향 |
|---|---|---|
| manage-us-stock-strategy/references/portfolio-exposure-review.md 259~274행 "Routine (Cowork, after the U.S. close, read-only Kiwoom CLI)" — `kiwoomcli overseas candles stock-minute` | Cowork 세션의 셸 | **이 줄 때문에 deny kiwoomcli 두 줄을 뺐다.** 훅 표지에는 남아 있다(D1) |
| manage-us-stock-strategy/scripts/collect_30m.ps1 49행 `cmd /c "kiwoomcli overseas candles stock-minute …"` | auto-core(run_auto_core.ps1 → auto_core.py 145행), Windows 작업 스케줄러 | Claude 도구 호출이 아니라 영향 없음. Claude가 `powershell -File …collect_30m.ps1`로 부르는 명령 문자열에도 표지가 없다(테스트로 통과 확인) |
| docs/claude/redesign-t2-firstrun-2026-10-13.ps1 17행 `Get-Command kiwoomcli` | 사장 터미널(1회성 진단) | 사장 터미널은 영향 없음 |
| kiwoom_runtime_bridge.py·kiwoom_account_readonly_bridge.py·regular_session_close_history.py | 주석과 저장 형식 설명뿐(호출은 런타임 라이브러리) | 영향 없음 |
| tools/dev_pipeline/builder-rules.md 5행 | 파이프라인 Builder에 kiwoomcli 실행 금지 | 같은 방향 |
| docs/claude/scheduled-prompts/** | 일치 0건 | — |

비교: tools/dev_pipeline/devpipe.py 122행에도 비슷한 `ORDER_MARKERS`가 있다(변경 범위 검사용). 훅은 `.claude/hooks`에서 혼자 돌아야 해서 그 목록을 가져다 쓰지 않았다. 두 목록은 따로 관리된다.

# 훅 표지 표
| 표지 | 정규식(대소문자 무시) | 적용 |
|---|---|---|
| kiwoomcli | `kiwoomcli` | 셸 명령, kiwoom MCP 입력 전체 |
| overseas orders | `overseas\s+orders` | 같음 |
| ust20000~20003 | `ust2000[0-3]` | 같음 |
| /api/us/ordr | `/api/us/ordr` | 같음 |
| --confirm | `--confirm(?![A-Za-z0-9_-])` | 같음 |
| confirm true (추가) | `(?<![A-Za-z0-9_-])confirm["']?\s*[:=]\s*["']?(true\|1\|yes\|on)(?![A-Za-z0-9_])` | 같음 |
| 주문 도구 이름 | 이름(소문자화)이 `kiwoom_order_submit`/`kiwoom_order_preview`로 끝남 | kiwoom MCP 도구 |
| 입력의 confirm 참 | 키를 정규화했을 때 `confirm`이고 값이 참(중첩 dict·list 포함) | kiwoom MCP 도구 |
인용·이스케이프 문자를 지운 문자열도 다시 검사한다.

## 거짓 양성 예 (막히는 일상 작업)
- Bash·PowerShell에서 표지 문자열이 든 명령: `grep -rn kiwoomcli …`, `rg "overseas orders"`, `git log --grep ust20000`, 커밋 메시지에 `--confirm`이 든 `git commit -m "…"`. 검색은 Grep 도구로 하면 된다(대상 아님). 커밋 메시지는 파일로 쓴 뒤 `git commit -F`로 하면 된다.
- `mcp__kiwoom_spec__spec_search`처럼 이름에 kiwoom이 든 문서 도구에서 `ust20000`·`overseas orders`를 찾는 일.
- `kiwoom_query`의 `overseas orders orderable-quantity`(ust31490, account_read) 조회. 이 API는 이미 workspace/policies/kiwoom-candidate-discovery-readonly-policy.json 32행 `blocked_api_ids`에 들어 있다.
- 훅이 발동하는 셸 도구에서의 읽기 전용 `kiwoomcli` 호출(D1)과 Cowork apply의 `--confirm`(D2).
- 테스트로 통과를 확인한 명령: `git status`, `python -m unittest discover …`, `validate_schema_contracts.py`, `--confirmed-via USER_TERMINAL`, `--confirmation-code-file`, `--confirm-export-path`, `--confirm_code_file=1`, `confirm_code=1 unconfirm=true confirmed=true`, `Get-ChildItem docs/claude`, `rg -n order_ticket docs/claude`, `kiwoom_runtime_bridge.py --help`, `powershell -File …collect_30m.ps1`, 그리고 평범한 `kiwoom_query`(`confirm: false` 포함)와 `kiwoom_commands`.

# 테스트
- 기준선(변경 전): `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline*"` → Ran 126, OK(실패 0). `-p "test_approval_human_check*"` → Ran 28, OK(실패 0).
- 변경 후: 같은 두 명령 → Ran 126 OK · Ran 28 OK. 새 실패 0. `test_auto_core*`는 이 변경과 관계없어 돌리지 않았다.
- 새 테스트: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_kiwoom_order_block_hook.py"` → Ran 21, OK. skip 0, 기존 테스트 수정 0.
  - 거절: 텍스트 표지 6종 × (Bash, PowerShell, `mcp__kiwoom_exec__kiwoom_query`, `mcp__remote-devices__device_bash`). 주문 도구 이름 4개(대소문자 섞음). confirm 참 8가지(중첩·문자열·`-confirm` 키·`"confirm: true"` 문자열)와 미리보기 도구의 confirm 옵션. 거짓 음성 변형 19개 × 3 셸 도구(`kiwoomcli.exe`, `KiwoomCLI.exe`와 앞뒤 줄바꿈, `kiwoom"cli`, `kiw^oomcli`, ``kiwoom`cli``, `"overseas" "orders"`, 공백 여러 개, 대문자, `"ust20001"`, `--confirm"`, `--confirm;`, `--confirm=1`, `--confirm=true`, `--CONFIRM`, 줄바꿈 뒤 `--confirm`, `{"confirm": true}`, `confirm: TRUE`). `start_process`·`interact_with_process`. 깨진 입력 6가지와 필드 없음 8가지는 모두 2.
  - 통과: 위 일상 명령 12개 × 3 셸 도구, 파일 쓰기 도구 5종에 표지가 든 경우, device_bash의 명령 아닌 필드에 표지가 든 경우, 이름에 kiwoom이 없는 MCP 도구, 대상이 아닌 도구의 이상한 입력.
  - 파일 형태: 훅은 ASCII·CRLF이고 import는 정확히 {json, re, sys}이며 `os.environ`·`getenv`·`argv`가 없다. 제안 파일은 ASCII·CRLF다.
  - 제안 settings 불변식: (a) 현재 deny가 제안 deny의 앞부분과 순서까지 같고, ask가 같다. (b) allow와 permissions 키 집합이 같다. (c) 추가 deny는 승인 목록 5줄 안에서 중복 없이 3~5줄이고, 필수 3줄이 있다. (d) 새 최상위 키는 `hooks`뿐이고 다른 키 값은 같다. 그리고 matcher가 대상 10개 이름을 덮고 파일 도구 8개는 덮지 않는다.

# ④ 결론 (자세한 내용: docs/claude/kiwoom-overseas-order-guard-2026-10-25.md)
**예, 보낸다.** `api_commands.csv` 286~289행은 `guarded`·`order_write`다. `safety.py` 9~20행은 `preview-only`일 때만 막고, `guarded` + confirm이면 통과시킨다. 이어서 `rest.py` 30~38행이 `fetch_page`를 부른다. `orders.py` 145~153·177~190행에서 `--confirm`을 받으면 실제 전송으로 간다. `argument_maps.py` 259~265행의 도움말도 CSV와 맞는다. 틀린 것은 server.py 271~272행 주석이다. 그리고 `kiwoom_order_preview`도 options의 confirm으로 실제 전송이 될 수 있다. 패키지는 고치지 않았다. 주석·코드 수정안은 문서에만 적었다(사장 결정, 별도 K3).

# ① 사장이 앱에서 직접 확인·고정할 단계 (코드 변경 없음, 주문 없음)
근거: 스위치는 환경값 `KIWOOM_MCP_ALLOW_ORDERS`이고 정확히 `1`일 때만 켜진다(kiwoom-order-block-review-2026-10-25.md 23행 → `.runtime-cache/kiwoom-mcp-20260928/mcp_exec/src/kiwoom_exec_mcp/config.py` 9·23·68행). 연동 문서는 "global execution MCP … order gate disabled"라고 적는다(kiwoom-mcp-local-integration.md 64~66행).
1. 키움 실행 서버(`kiwoom_exec`)가 어디에 등록돼 있는지 먼저 봅니다. Claude 데스크톱 앱이라면 설정 → 개발자(Developer) → MCP 서버 목록에서 `kiwoom_exec`를 엽니다. **메뉴 이름은 확인 필요**이니, 못 찾으면 화면 이름만 알려 주세요.
2. 그 서버의 환경(env) 목록에서 `KIWOOM_MCP_ALLOW_ORDERS`만 봅니다. 값은 **항목 없음 또는 `0`** 이어야 합니다. 앱ID·시크릿 같은 다른 값은 열거나 복사하거나 화면에 띄우지 마세요. 설정 파일을 직접 여는 방식이면 그 줄만 보고 닫으세요.
3. `1`이면 `0`으로 바꾸거나 그 줄을 지우고 저장한 뒤, 앱을 완전히 끄고 다시 켭니다.
4. 같은 서버가 Claude Code에도 등록돼 있다면, 새 Claude Code 세션에서 `/mcp`를 열어 `kiwoom_exec`의 도구 목록에 `kiwoom_commands`·`kiwoom_help`·`kiwoom_query` 3개만 있는지 봅니다. `kiwoom_order_submit`·`kiwoom_order_preview`가 보이면 스위치가 켜진 것입니다. 이 방법은 비밀 값을 보지 않습니다.
5. 결과를 "없음/0/1" 한 단어로 알려 주세요. 고정은 "0 또는 없음"을 유지하는 것이고, 저장소에서 할 일은 없습니다.

# 병합 뒤 확인 (무해, 사장 또는 코디네이터)
1. 병합 스크립트는 제안 파일을 **바이트 그대로**(CRLF) `.claude/settings.json` 자리에 복사하고, `.claude/hooks/kiwoom_order_block.py`도 같은 커밋에 넣어야 합니다. 훅 파일이 없으면 `python`이 "can't open file"로 종료 코드 2를 내서 모든 Bash·PowerShell 호출이 막힙니다(fail closed).
2. 새 Claude Code 세션에서 `echo ust20000`을 실행해 달라고 합니다. **거절되면** 훅 형식이 맞는 것입니다. 그냥 실행되면 후보 2 형식으로 바꿔야 합니다. 이 명령은 화면에 글자를 찍을 뿐 키움과 무관합니다.
3. (fix1) 새 Claude Code 세션에서 **Monitor 도구로** `echo ust20000`을 실행해 달라고 합니다. **거절되면 정상**입니다. 그냥 실행되면 matcher의 `Monitor` 이름이나 훅 입력 형태가 실제와 다른 것이니 알려 주세요. 이 명령도 화면에 글자를 찍을 뿐 키움과 무관합니다.
4. 원격 장치 스레드에서 같은 시험을 해 보면 발동 여부를 알 수 있습니다(지금은 확인 필요).
5. (fix3) fix3 병합 뒤 메인에서 세 테스트 묶음을 돌립니다. 기대값은 모두 OK, 실패 0, skip 0입니다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_kiwoom_order_block_hook.py"` → Ran 25 · `-p "test_dev_pipeline*"` → Ran 126 · `-p "test_approval_human_check*"` → Ran 28. (훅 테스트가 23개에서 25개가 된 것은 fix3가 settings 시험 2개를 더했기 때문입니다.) fix3 병합 전 메인(c9c0877)에서는 이 중 3건이 실패합니다(아래 "fix3 반영").

# 한계
- **훅이 `mcp__remote-devices__*` 도구와 Cowork 세션에서 발동하는지는 확인 필요다.** 하위 에이전트의 문서 요약(code.claude.com/docs/en/settings.md, desktop.md)에서도 문서화되지 않았다고 했다. 이 세션은 읽기만 했기 때문에 증명할 수 없다. 클라우드 "프로젝트 스레드"에서는 저장소 `.claude/settings.json`의 훅과 권한이 적용되지 않는다는 요약도 있었다(원문 대조는 확인 필요).
- 훅 matcher와 command 형식이 Windows에서 실제로 발동하는지는 병합 전에 증명할 수 없다(병합 뒤 확인 2).
- 훅은 도구 입력 문자열만 본다. 다음은 못 막는다(fix1 전·후 모두): PowerShell `-EncodedCommand`(base64), 변수로 이어 붙인 문자열(`$a='kiwoom'+'cli'`), bash brace 확장(`--confi{rm,rm}`), 명령 치환(`$(…)`), 변수 확장(`${x}`), 파일 쓰기 도구로 스크립트를 쓴 뒤 `python x.py`로 실행하기, 환경변수 간접 참조. deny 패턴도 같은 한계가 있다. **키움 스위치 `0`(①)은 이 CLI 경로를 막지 않는다.** `kiwoom_cli`와 런타임 패키지는 `KIWOOM_MCP_ALLOW_ORDERS`를 읽지 않는다(grep 0건, 근거 줄은 아래 "fix1 반영" 절과 guard 문서 결론 4). 스위치 ①은 MCP 주문 도구만 막는다. CLI 경로를 막는 것은 deny `overseas orders` 2줄 + 이 훅 + 지침뿐이고, 위 우회들에서는 지침만 남는다.
- (fix3, 2차 Judge F10) **인용·`$'…'`를 여러 개로 쪼갠 변형 가운데 세 검사 형태(원문, 따옴표만 지운 것, 넓게 지운 것) 어느 것으로도 표지가 되지 않는 계열이 있다.** 넓게 지운 형태에서 `$'\0'`이 `0`으로 남아 `--confirm` 뒤 경계에 막히거나(`--con\firm$'\0'`, `--con$''firm$'\0'`, `--con""fi$'r'm$'\0'`), `$'…'` 안의 이스케이프가 풀리지 않기 때문이다(`$'--con\x66irm'`). 같은 이유로 bash brace 확장(`--confi{rm,}`), 변수 확장(`--con${x}rm`, `x=fi`), 명령 치환(`--con$(printf fi)rm`)도 통과한다. fix3 세션에서 이 7개를 `python -m kiwoom_cli domestic orders buy <값>` 꼴의 Bash 합성 입력으로 현재 훅(sha256 2818d79f…)에 넣었더니 모두 종료 코드 0(통과)이었다. Git Bash `printf '[%s]\n' <값>`으로는 7개 모두 `--confirm`이 됐다(brace는 `--confirm`·`--confi` 두 단어). 이 계열을 막는 코드 보강은 이번 범위 밖이다(기본값 NO_CHANGE). 이 경우 셸 경로에 남는 방어는 지침뿐이다(해외 주문은 deny `overseas orders` 2줄도 남음).
- 문서 사실(matcher 의미, `onFailure`, 시간 초과 fail open, 쉘 종류)은 하위 에이전트가 가져온 요약이라 이 세션에서 원문을 열지 않았다. Judge가 원문을 대조하기 전까지는 확인 필요로 둔다.

# 남은 위험
- 국내 주문 `kiwoomcli domestic orders buy --confirm`(kt10000 등, `guarded`·`order_write`)은 deny에 없다. `overseas orders`만 넣었고 kiwoomcli 두 줄은 뺐기 때문이다. 훅의 `kiwoomcli`·`--confirm` 표지만 막는다. D1에서 (b)를 고르면 `--confirm` 표지 하나만 남는다.
- `Bash(*overseas orders*)` deny는 공백 한 칸에만 맞는다. 공백 두 칸이나 따옴표로 나눈 경우는 훅이 맡는다.
- `onFailure: block`과 command 형식 오류가 겹치면 모든 셸 도구가 막힌다. 안전한 방향이지만 작업이 멈출 수 있다. 되돌리는 방법은 `hooks` 절 삭제다.
- `kiwoom_order_preview`의 confirm 우회는 스위치가 `1`일 때만 존재한다. 패키지 쪽 수정은 하지 않았다(제안만).

# 하지 않은 것
키움 도구·CLI 실행 0건(`kiwoom_commands` 포함). 인증·토큰·`.env`·`.runtime-cache/kiwoom-mcp-20260928/private-data`·전역 설정·계좌 정보 읽기 0건. auto_core.py·apply·dev-run·dev-merge·dev-queue 실행 0건. `.claude/settings.json`·CLAUDE.md·tools/**·정책·상태 파일 수정 0건. 설치된 키움 패키지 수정 0건(읽기만). 커밋·push·병합 0건. 병합 스크립트는 허용 파일 밖이라 만들지 않았다. BLOCKED.md도 없다.

# 새 파일 sha256 (CRLF 그대로)
| sha256 | 바이트 | 파일 |
|---|---|---|
| 2818d79fcdd5ee2083be65c888447ea84a04f75188ca35376a5b2038c87cc81f | 5971 | .claude/hooks/kiwoom_order_block.py (fix2) |
| 459cd04f0dee5aa915fafc0397af2369b9348aab19632505df953d466ea36942 | 1952 | docs/claude/kiwoom-block-settings-proposed.json (fix1, fix2에서 변경 없음) |
| 36f4b3a928ac6074220f6bf1a42d4890e5cd3988ea3cbfae3cd63a7d94442864 | 8071 | docs/claude/kiwoom-overseas-order-guard-2026-10-25.md (fix1, fix2에서 변경 없음) |
| 859b57e8d91cb8f18fa6353252021f893d580c37af40a7e409cc4fcfb8f5a30b | 19507 | manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py (fix2) |
| (자기 자신은 적을 수 없음 — Judge가 계산) | — | docs/claude/kiwoom-block-builder-report.md |

fix1 전 값(1차 Judge가 본 값): 훅 ef29c530f47871d2a7e03471229ef68ff38a802285e367d04f334e83be87ebfc(5546) · 제안 settings 3d962caffcef9e18d8c697e9bf65ea1c4ce4c8dba482a01dbae081c354428a5e(1944) · guard 문서 0408583f1ab570db01bc145894ee7e86cab789800df006afb44dc2331bc1b346(7180) · 테스트 2b896b17330ed088565d267137f3c1e9a0d69cf6311c572c1d902f8471977f50(16072). fix1 Builder가 수정을 거꾸로 되돌린 사본으로 네 값이 모두 일치함을 확인했다(아래 diff는 그 사본과 현재 파일의 비교).
fix1 값(2차 Judge가 본 값): 훅 375206d7b9bb9699d23af747c4c50127bdec1749d3a945957a2a15ebce0f3167(5793) · 테스트 4a9f27f47f7ab21c1f24b52419dc0a9e678e9f9914966903d4dcf40d67f9c015(17448). fix2 Builder가 수정 전에 두 파일의 값이 이와 같음을 확인했다.
참고: 현재 `.claude/settings.json`은 f793271fad76954a640e5111fd4d03293a265298ec664b8f8ab1aedfb5cfdfe5(1384바이트)이고 변경하지 않았다.

# fix1 반영 (2026-10-25, Judge PASS_WITH_FIX 수정안 F1~F5)
지시문: docs/claude/kiwoom-block-fix1-prompt.md (출처: Judge VERDICT PASS_WITH_FIX, 사장이 스레드에 직접 붙인 수정안, 2026-10-25 12:04:09Z). 위의 원래 결론은 지우지 않았고, 이 절에 바뀐 점만 적는다. 수정한 곳은 위 본문의 matcher 문단, "병합 뒤 확인", "한계", sha256 표다.

## 결론
1. **F1~F5를 모두 반영했다.** 바뀐 파일은 5개이고 모두 기존 미커밋 새 파일이다. 허용 파일 밖 수정, `.claude/settings.json`·CLAUDE.md·tools/** 수정, 키움 도구·CLI 실행, 키움 패키지 수정, 비밀 접근, 커밋·push·병합은 모두 0건이다. D1·D2는 바꾸지 않았다(현행 유지). 새 표지와 deny 변경도 없다.
2. **(fix2 정정) "훅은 거절만 늘었다"는 fix1 처음 판에서 사실이 아니었다.** fix1 처음 판은 정리본을 바꿔 끼워, fix1 전에 걸리던 입력(`--con""firm$'\0'` 등, bash에서 `--confirm`이 됨)이 통과했다. fix2는 따옴표만 지운 정리본도 함께 검사해 fix1 전 거절을 모두 되살린다. (처음 문장 "원래 문자열 검사는 그대로 하고 정리본 검사를 더 하는 구조도 같다"가 틀렸다. 정리본을 더한 것이 아니라 바꿔 끼웠다.) 대상 도구에 `Monitor`를 더한 것과 대상이 아닌 도구가 그대로 0이라는 점은 맞다. 자세한 내용은 아래 "fix2 반영" 절에 있다.
3. **테스트**: 훅 테스트는 Ran 22, OK이다(21개에서 새 테스트 1개를 더했고, 기존 테스트 2개에 케이스를 더함). `test_dev_pipeline*`은 Ran 126, OK이고 `test_approval_human_check*`는 Ran 28, OK이다. fix1 전 기준선(21 / 126 / 28, 모두 OK)과 비교해 새 실패 0, skip 0, 단언 약화 0이다.
4. **지시문보다 더 한 것은 1건이다(거절만 늘림).** 정리 정규식이 백슬래시+줄바꿈(`\\\r?\n`)도 지운다. F2는 주석에 "백슬래시 줄바꿈 이스케이프"를 적으라고 했는데, 예시 정규식만으로는 bash 줄 잇기 `--con\<줄바꿈>firm`(= `--confirm`)이 걸리지 않아 주석이 사실과 달라진다. 그래서 거짓 음성 목록에 이 변형을 하나 더 넣었다(지시문 3개 + 1개). 빼려면 정규식 앞의 `\\\r?\n|`와 테스트 한 줄을 지우면 된다.

## 파일별 변경
| F | 파일 | 변경 |
|---|---|---|
| F1 | `.claude/hooks/kiwoom_order_block.py` | docstring 7행에 Monitor를 넣고 29행을 `SHELL_TOOLS = ("Bash", "PowerShell", "Monitor")`로 바꿈. `command` 필드가 없는 Monitor 호출(ws만 씀)은 기존 규칙대로 거절(fail closed) |
| F2 | 같은 파일 | 36행 `STRIP_CHARS = re.compile(r"\\\r?\n\|[\"'`^\\]\|\$(?=[\"'])")`(Python에서 직접 검증), 32~35행 주석에 bash 백틱·`$'…'`·백슬래시·백슬래시 줄바꿈을 적음 |
| F3 | `docs/claude/kiwoom-block-settings-proposed.json` | 46행 matcher에 `Monitor\|`만 넣음. 다른 줄은 바이트까지 같다(fix1 전 사본과 비교해 1줄만 바뀜) |
| F4 | `manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py` | `targets`에 `"Monitor"`. 거짓 음성 변형 4개(`--con\firm`, `kiwoom\cli`, `--con$'f'irm`, `--con\<줄바꿈>firm`) × 3 셸 도구 거절. `test_monitor_command_is_checked`: 표지가 있으면 2, `git status`는 0, `ws`만 있으면 2. 일상 명령에 Windows 경로 명령 3개 × 3 셸 도구 통과: `python C:\Users\TEST_ONLY\AppData\Local\Temp\x.py`, `Get-ChildItem E:\사업\##금동한\코덱스저장소\docs\claude`(테스트 파일은 ASCII라 `\u` 이스케이프로 적고, 값이 이 문자열과 같은지 ast로 확인), `python manage-us-stock-strategy\scripts\validate_schema_contracts.py` |
| F5 | `docs/claude/kiwoom-overseas-order-guard-2026-10-25.md` | 결론 4: CLI와 런타임은 스위치를 읽지 않고, 스위치 ①은 MCP 주문 도구만 막으며, CLI 경로는 deny `overseas orders` 2줄 + 훅 + 지침뿐이라고 고침. 근거표 `kiwoom_query` 줄 번호를 "36·207~217행"으로 고치고 `_guard` 79~97행을 따로 적음 |
| F5 | `docs/claude/kiwoom-block-builder-report.md` | matcher 괄호 교대 "확인 필요"를 해소로 바꿈. "병합 뒤 확인" 3번(Monitor 시험)을 넣어 원래 3번은 4번이 됨. "한계"의 스위치 문장을 정정하고 못 막는 예 3개(brace 확장, `$(…)`, `${x}`)를 추가. sha256 표 갱신. 이 절 추가 |

## F5 근거 (읽기만, 이 세션에서 직접 grep·열람)
경로 앞부분은 guard 문서와 같다: `K = .runtime-cache/kiwoom-mcp-20260928/mcp_exec`.
- `K/.venv/Lib/site-packages/kiwoom_cli`(py 28개)와 `K/.venv/Lib/site-packages/kiwoom`(py 20개)에서 `grep -rniE "allow_orders|KIWOOM_MCP"`(모든 파일)는 0건이다. Grep `ALLOW_ORDERS`(대소문자 무시)도 두 폴더 모두 0건이다.
- `K/src`에서 Grep `ALLOW_ORDERS`: `kiwoom_exec_mcp/config.py` 9행(주석), 23행 `ENV_ALLOW_ORDERS = "KIWOOM_MCP_ALLOW_ORDERS"`, 68행 `allow_orders=env.get(ENV_ALLOW_ORDERS) == "1"`, `server.py` 47행(도움말 문구). 이 값을 쓰는 곳은 `server.py` 252행 `if SETTINGS.allow_orders:`이다.
- `server.py`: 36행은 `READ_POLICIES = {"read", "account_read"}`이다. 207~217행은 `async def kiwoom_query`부터 `return await _guarded_query(command_path, options, READ_POLICIES)`까지다. 79~97행은 `_guard`(정책이 다르면 error dict)이다.
- matcher 의미: code.claude.com/docs/en/hooks.md(2026-10-25 WebFetch). "Contains any other character → JavaScript regular expression, unanchored", "tested with JavaScript's `RegExp.prototype.test`". 이 페이지 앞 10만 자에는 Monitor 도구에 대한 문장이 없었다.

## 새로 생기는 거짓 양성 (거절이 늘어난 몫)
- 셸 명령에 백슬래시를 지우면 표지가 되는 Windows 경로가 있으면 거절된다. 예: `python E:\x\kiwoom\cli.py`(→ `kiwoomcli`). 저장소 경로와 일상 명령은 해당하지 않는다(테스트 통과).
- Monitor 도구에서 표지가 든 명령(예: `tail -f log | grep ust20000`)도 거절된다. Monitor는 Bash와 같은 셸에서 돌기 때문에 의도된 동작이다. 로그 감시는 표지 없는 패턴으로 하면 된다.
- `ws`만 쓰는 Monitor 호출은 `command`가 없어 항상 거절된다(F1이 정한 fail closed).

## 한계 (fix1 추가)
- matcher의 `Monitor`가 실제 훅 이벤트의 `tool_name`과 같은지는 읽기로 증명할 수 없다. 이 세션 도구 목록의 이름이 `Monitor`이고, 입력 필드가 `command`/`ws`(도구 스키마)라는 것까지만 확인했다. 병합 뒤 확인 3번이 판정한다.
- 백슬래시 정리는 bash 기준이다. PowerShell 줄 잇기(백틱+줄바꿈)는 백틱만 지워지고 줄바꿈이 남는다. 단어 중간에 넣은 PowerShell 줄 잇기가 한 단어로 이어지는지는 확인 필요다(이어진다면 못 막음). fix1 범위 밖이라 고치지 않았다.

## F1~F4 diff (fix1 전 사본 → 현재, CRLF는 표시에서 뺌)

```diff
--- a/.claude/hooks/kiwoom_order_block.py
+++ b/.claude/hooks/kiwoom_order_block.py
@@ -4,7 +4,7 @@
 Reads the hook JSON from stdin. Exit 2 (refuse, one-line reason on stderr) when a target tool's input
 carries an order marker, or when a target tool's input cannot be read (fail closed); otherwise exit 0.
 
-Targets: Bash and PowerShell (field "command"); mcp__ tools whose name contains "kiwoom" (the whole input);
+Targets: Bash, PowerShell and Monitor (field "command"); mcp__ tools whose name contains "kiwoom" (the whole input);
 mcp__ tools that run a shell on a device, named ending in device_bash, start_process or
 interact_with_process (the command field only). File-writing tools are never targets, so documents may
 quote the markers. This hook only adds refusals: it has no allow path, no bypass switch and no test branch.
@@ -26,12 +26,14 @@ MARKERS = (
                                 re.IGNORECASE)),
 )
 ORDER_TOOL_SUFFIXES = ("kiwoom_order_submit", "kiwoom_order_preview")
-SHELL_TOOLS = ("Bash", "PowerShell")
+SHELL_TOOLS = ("Bash", "PowerShell", "Monitor")
 DEVICE_SHELL_SUFFIXES = ("device_bash", "start_process", "interact_with_process")
 DEVICE_COMMAND_FIELDS = ("command", "cmd", "input", "script")
 # Shell quoting and escape characters are dropped before matching, so kiwoom"cli, kiw^oomcli,
-# kiwoom`cli and "overseas" "orders" still match. This can only add matches.
-STRIP_CHARS = re.compile(r"[\"'`^]")
+# kiwoom`cli and "overseas" "orders" still match. Also dropped: the bash backtick, the $ of bash $'...'
+# and $"...", backslashes and backslash-newline escapes, so --con\firm, kiwoom\cli, --con$'f'irm and
+# a --con\<newline>firm continuation match too. This can only add matches.
+STRIP_CHARS = re.compile(r"\\\r?\n|[\"'`^\\]|\$(?=[\"'])")
 TRUE_TEXT = {"true", "1", "yes", "y", "on"}
 
 
--- a/docs/claude/kiwoom-block-settings-proposed.json
+++ b/docs/claude/kiwoom-block-settings-proposed.json
@@ -43,7 +43,7 @@
   "hooks": {
     "PreToolUse": [
       {
-        "matcher": "^(Bash|PowerShell|mcp__.*[Kk][Ii][Ww][Oo][Oo][Mm].*|mcp__.*(device_bash|start_process|interact_with_process))$",
+        "matcher": "^(Bash|PowerShell|Monitor|mcp__.*[Kk][Ii][Ww][Oo][Oo][Mm].*|mcp__.*(device_bash|start_process|interact_with_process))$",
         "hooks": [
           {
             "type": "command",
--- a/manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py
+++ b/manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py
@@ -118,6 +118,10 @@ class HookRefusesOrderMarkers(unittest.TestCase):
             "python -m kiwoom_cli exchange request --confirm=true",
             "echo '{\"confirm\": true}' > x.json",
             "echo confirm: TRUE",
+            r"python -m kiwoom_cli domestic orders buy --con\firm",
+            r"kiwoom\cli --version",
+            "python -m kiwoom_cli domestic orders buy --con$'f'irm",
+            "python -m kiwoom_cli domestic orders buy --con\\\nfirm",
         )
         for text in variants:
             for family in ("Bash", "PowerShell", "device_bash"):
@@ -132,6 +136,17 @@ class HookRefusesOrderMarkers(unittest.TestCase):
         self.assert_refused("mcp__plugin_desktop-commander_desktop-commander__interact_with_process",
                             {"pid": 1, "input": "kiwoomcli overseas orders sell --confirm"})
 
+    def test_monitor_command_is_checked(self):
+        # Monitor runs its command in the same shell as Bash; a ws-only call has no command and is refused.
+        self.assert_refused("Monitor", {"command": "echo ust20000", "description": "x", "timeout_ms": 1000})
+        self.assert_refused("Monitor", {"command": "python -m kiwoom_cli domestic orders buy --con\\firm",
+                                        "description": "x", "timeout_ms": 1000})
+        code, stderr = run_tool("Monitor", {"command": "git status", "description": "x", "timeout_ms": 1000})
+        self.assertEqual(code, 0, stderr)
+        code, _ = run_tool("Monitor", {"ws": {"url": "wss://example.invalid/stream"}, "description": "x",
+                                       "timeout_ms": 1000})
+        self.assertEqual(code, 2)
+
     def test_unreadable_or_incomplete_input_is_refused(self):
         for stdin_bytes in (b"", b"not json", b"{\"tool_name\": \"Bash\"", b"[]", b"null",
                             b"\xff\xfe\x00garbage"):
@@ -168,7 +183,10 @@ class HookPassesOrdinaryWork(unittest.TestCase):
                      "Get-ChildItem docs/claude",
                      "rg -n order_ticket docs/claude",
                      "python manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py --help",
-                     "powershell -File manage-us-stock-strategy/scripts/collect_30m.ps1 -Symbol NVDA"):
+                     "powershell -File manage-us-stock-strategy/scripts/collect_30m.ps1 -Symbol NVDA",
+                     r"python C:\Users\TEST_ONLY\AppData\Local\Temp\x.py",
+                     "Get-ChildItem E:\\\uc0ac\uc5c5\\##\uae08\ub3d9\ud55c\\\ucf54\ub371\uc2a4\uc800\uc7a5\uc18c\\docs\\claude",
+                     r"python manage-us-stock-strategy\scripts\validate_schema_contracts.py"):
             for family in ("Bash", "PowerShell", "device_bash"):
                 tool_name, build = TARGET_TOOLS[family]
                 with self.subTest(text=text, family=family):
@@ -265,7 +283,7 @@ class ProposedSettingsOnlyAdd(unittest.TestCase):
         self.assertEqual(len(commands), 1)
         self.assertEqual(commands[0]["type"], "command")
         self.assertIn(".claude/hooks/kiwoom_order_block.py", commands[0]["command"])
-        targets = ("Bash", "PowerShell", "mcp__kiwoom_exec__kiwoom_query", "mcp__kiwoom_exec__kiwoom_order_submit",
+        targets = ("Bash", "PowerShell", "Monitor", "mcp__kiwoom_exec__kiwoom_query", "mcp__kiwoom_exec__kiwoom_order_submit",
                    "mcp__kiwoom_exec__kiwoom_commands", "mcp__kiwoom_spec__spec_search",
                    "mcp__remote-devices__device_bash", "mcp__remote-devices__start_process",
                    "mcp__plugin_desktop-commander_desktop-commander__start_process",
```

## F5 diff (guard 문서; 보고서 자체의 변경은 위 "파일별 변경" 표 참고)

```diff
--- a/docs/claude/kiwoom-overseas-order-guard-2026-10-25.md
+++ b/docs/claude/kiwoom-overseas-order-guard-2026-10-25.md
@@ -13,7 +13,9 @@ authority: "order_authority=false · quantity_authority=none"
 1. **`--confirm`으로 실제 전송이 되는가: 예.** 설치된 `kiwoom_cli`는 `overseas orders buy/sell/modify/cancel`(ust20000~20003)을 `coverage=guarded`로 읽고, `guarded` + `order_write` + `--confirm`이면 안전 검사를 통과해 `/api/us/ordr`로 요청을 보낸다. CLI 층에서 해외 주문을 막는 코드는 없다.
 2. **주석과 CSV 중 맞는 쪽: CSV(`guarded`).** `server.py` 271~272행 "Overseas order writes stay blocked by the CLI even with --confirm while coverage is preview-only"는 지금 설치본과 맞지 않는 옛 주석이다. CSV 비고에도 "Guarded after real-call CLI round-trip verification"이라고 적혀 있다.
 3. **새로 찾은 경로: `kiwoom_order_preview`도 실제 주문을 낼 수 있다.** 미리보기 도구는 `options`를 그대로 CLI 플래그로 바꾸므로 `options={"confirm": true}`(또는 키 `-confirm`/`--confirm`)이면 `--confirm`이 붙어 실제 전송된다. 도구 설명 "no order is ever submitted under any condition"(server.py 257행)과 `readOnlyHint: True`(293~294행)는 코드와 맞지 않는다. 이 도구는 스위치 `KIWOOM_MCP_ALLOW_ORDERS=1`일 때만 생긴다(server.py 252행).
-4. 따라서 Claude 쪽에서 이 경로들을 막는 층은 (가) 키움 스위치 `0`(①), (나) deny `mcp__*__kiwoom_order_submit`(기존)·`mcp__*__kiwoom_order_preview`·`Bash/PowerShell(*overseas orders*)`(②), (다) 주문 표지 훅(③)이다. CLI 자체는 막지 않는다.
+4. 따라서 Claude 쪽에서 이 경로들을 막는 층은 경로마다 다르다. **`kiwoom_cli`와 런타임 패키지(`kiwoom`)는 `KIWOOM_MCP_ALLOW_ORDERS`를 읽지 않는다**(`C/**`·`K/.venv/Lib/site-packages/kiwoom/**` grep `ALLOW_ORDERS|KIWOOM_MCP`(대소문자 무시) 0건. 이 스위치를 읽는 곳은 `K/src/kiwoom_exec_mcp/config.py` 23·68행과 이를 쓰는 `server.py` 252행 `if SETTINGS.allow_orders:`뿐이다). 그래서:
+   - **스위치 ①은 MCP 주문 도구만 막는다.** 스위치 `0`이면 `kiwoom_order_submit`·`kiwoom_order_preview`가 생기지 않는다. MCP 쪽은 이 스위치 + deny `mcp__*__kiwoom_order_submit`(기존)·`mcp__*__kiwoom_order_preview`(②) + 훅(③)이 막는다.
+   - **CLI 경로(셸에서 `kiwoomcli`·`python -m kiwoom_cli`)는 스위치와 무관하다.** 이 경로를 막는 것은 deny `Bash(*overseas orders*)`·`PowerShell(*overseas orders*)` 2줄(②) + 주문 표지 훅(③) + 지침뿐이다. 국내 주문(`domestic orders`)은 deny에도 없어 훅과 지침뿐이다. CLI 자체는 막지 않는다.
 
 # 근거 (원문 file:line, 이 세션에서 읽음)
 경로 앞부분: `K = .runtime-cache/kiwoom-mcp-20260928/mcp_exec` (본 저장소 작업 폴더, git 미추적), `C = K/.venv/Lib/site-packages/kiwoom_cli`.
@@ -33,7 +35,7 @@ authority: "order_authority=false · quantity_authority=none"
 | 틀린 주석 | 같은 파일 271~272행 | "Overseas order writes stay blocked by the CLI even with --confirm while coverage is preview-only" — 설치본 CSV는 `guarded` |
 | MCP 미리보기 도구 | 같은 파일 254~263·293~294행 | `_guarded_query(command_path, options, ORDER_POLICIES)`; 설명 "no order is ever submitted under any condition", `readOnlyHint: True` |
 | options → 플래그 | 같은 파일 114~122·142~147행, `K/src/kiwoom_exec_mcp/runner.py` 190~202행 | `args = [*parts, *options_to_args(options)]`; `options_to_args`는 키를 `--{key.replace('_','-').lstrip('-')}`로 바꾸고 값이 `True`면 플래그만 붙임 → `{"confirm": true}` = `--confirm` |
-| `kiwoom_query` | 같은 파일 37·79~97행 | `READ_POLICIES`만 받음 → `order_write` 명령은 `_guard`에서 거절. 읽기 명령에는 `--confirm` 인자가 없어 넣어도 인자 오류 |
+| `kiwoom_query` | 같은 파일 36·207~217행 (`READ_POLICIES`는 36행, `kiwoom_query`는 207~217행; 거절하는 `_guard`는 79~97행) | `READ_POLICIES`만 받음 → `order_write` 명령은 `_guard`에서 거절. 읽기 명령에는 `--confirm` 인자가 없어 넣어도 인자 오류 |
 | 환전 신청 | `C/maps/api_commands.csv` 314행 | `overseas exchange request`(ust31302)도 `guarded`·`order_write`·`--confirm`이면 전송 — 주문은 아니지만 같은 패턴. 훅의 `--confirm` 표지가 셸 경로를 막음 |
 
 확인하지 않은 것: 키움 서버가 이 계좌에서 주문을 실제로 접수하는지(계좌·인증 상태). 이 문서는 "CLI가 요청을 보내는가"만 판단한다. 실제 실행은 하지 않았다.
```

## Judge 재확인 항목 대응
| 항목 | 상태 |
|---|---|
| R1 변경이 F1~F5 안뿐 | 예. 단, 결론 4의 백슬래시+줄바꿈 1건은 F2 주석 문구를 사실로 만들려고 더한 것이다(거절만 늘림) |
| R2 훅이 거절만 더함 | fix1 처음 판은 아니오(judge2에서 회귀 확인), fix2 뒤 예. fix1 처음 판은 정리본을 바꿔 끼워 `--con""firm$'\0'` 같은 fix1 전 거절 입력이 통과했다. fix2는 원문, 따옴표만 지운 정리본, 넓은 정리본을 모두 검사한다(아래 "fix2 반영") |
| R3 우회 변형 거절, 일상·Windows 경로 통과 | 테스트로 확인(Bash·PowerShell·device_bash, Monitor는 별도 테스트) |
| R4 제안 settings 불변식 | `ProposedSettingsOnlyAdd` 6개 통과, matcher 1줄만 바뀜 |
| R5 문서 정정이 grep 근거와 맞음 | 위 "F5 근거"에 file:line |
| R6 테스트 전부 통과 | 22 / 126 / 28 OK |

# fix2 반영 (2026-10-25, 2차 Judge PASS_WITH_FIX 수정안 F6~F8)
지시문: docs/claude/kiwoom-block-fix2-prompt.md (출처: 2차 Judge VERDICT PASS_WITH_FIX, 사장이 스레드에 직접 붙인 수정안 F6~F8, 2026-10-25 13:07:28Z). 위의 원래 결론과 fix1 절은 지우지 않았다. 고친 곳은 fix1 결론 2, fix1 "Judge 재확인 항목 대응"의 R2 행, sha256 표, 그리고 이 절이다. 지시문의 줄 번호(훅 35·36·59행, 테스트 120행 근처, 보고서 145·148·159·317행)는 수정 전 파일과 모두 맞았다.

## 결론
1. **회귀를 고쳤다.** 훅 `find_marker`가 원문, 따옴표만 지운 정리본(`QUOTE_CHARS`, fix1 전 정리 글자와 같음), 넓은 정리본(`STRIP_CHARS`, fix1과 같음)을 모두 검사한다. 하나라도 표지에 걸리면 거절한다. 그래서 지금 훅이 거절하는 입력은 정확히 **(fix1 전 훅이 거절하던 입력) ∪ (fix1 처음 판이 거절하던 입력)**이다. Monitor는 fix1에서 더한 대상이다.
2. **회귀 입력 재현.** 2차 Judge가 bash로 확인한 입력(지시문 15행)은 `--con""firm$'\0'`와 `--con''firm$'\x00'`이다. 이 세션에서도 Git Bash `printf '[%s]\n' --con""firm$'\0' --con''firm$'\x00'`로 두 값이 모두 `[--confirm]`이 되는 것을 다시 확인했다(키움과 무관한 출력 명령). 훅에 `python -m kiwoom_cli domestic orders buy <위 값>`을 Bash 입력으로 넣으면 fix1 처음 판(sha256 375206d7…)은 **종료 코드 0(통과)**, fix2 훅은 **2(거절, 표지 `--confirm`)**를 낸다. 원인: 넓은 정리본은 `""`, `$'`, `'`, `\`를 모두 지워 `--confirm0`이 된다. `0`은 `--confirm` 뒤 경계(`(?![A-Za-z0-9_-])`)에 막힌다. 따옴표만 지운 정리본은 `--confirm$\0`이 되어 `$`가 경계 노릇을 한다.
3. **"This can only add matches"는 fix2 뒤에 사실이다(코드로 확인).** (가) `MARKERS`는 바뀌지 않았다(fix1 전 재구성본과 패턴·플래그가 같음). (나) 검사하는 변형 튜플 `(text, QUOTE_CHARS.sub, STRIP_CHARS.sub)`는 fix1 전의 `(text, 따옴표 정리본)`과 fix1의 `(text, 넓은 정리본)`을 모두 포함한다. (다) `check()`의 다른 경로(대상 판정, 주문 도구 이름, confirm 키, fail closed)는 바뀌지 않았다. (라) 거절 조건은 "어느 변형이든 걸리면"이다. 따라서 거절 집합은 두 판의 합집합이고, 줄어든 곳도 새로 생긴 곳도 없다. 무작위 입력 20만 개(표지 조각, 따옴표, 백슬래시, `$`, 줄바꿈 조합, seed 20261025)로 세 판의 `find_marker`를 비교했다. fix1 전 판만 거절한 입력 0, fix1 판만 거절한 입력 0, 두 판 모두 통과시켰는데 지금 판만 거절한 입력 0이다. 반대로 fix1 처음 판에서 같은 문장은 fix1 전 대비 **사실이 아니었다**(이 절 2번).
4. **새 거짓 양성 없음.** 더한 변형(따옴표만 지운 정리본)은 fix1 전 훅이 쓰던 그대로다. 이것으로 새로 거절되는 입력은 fix1 전에도 거절되던 입력뿐이다. 일상 명령·Windows 경로 통과 테스트는 그대로 통과한다.
5. **테스트**: 훅 테스트 Ran 23, OK(22개 + 새 테스트 1개). `test_dev_pipeline*` Ran 126, OK. `test_approval_human_check*` Ran 28, OK. 새 실패 0, skip 0, 단언 약화 0.
6. 바뀐 파일은 3개다: 훅, 테스트, 이 보고서. 제안 settings와 guard 문서는 바이트까지 같다(sha256 위 표). 허용 파일 밖 수정, `.claude/settings.json`·CLAUDE.md·tools/** 수정, 키움 도구·CLI 실행, 키움 패키지 수정, 비밀 접근, 커밋·push·병합은 모두 0건이다. D1·D2는 현행 유지했고, 새 표지와 deny 변경도 없다. BLOCKED.md도 없다.

## F6 훅 diff (fix1 사본 → 현재, CRLF는 표시에서 뺌)

```diff
@@ -32,7 +32,9 @@ DEVICE_COMMAND_FIELDS = ("command", "cmd", "input", "script")
 # Shell quoting and escape characters are dropped before matching, so kiwoom"cli, kiw^oomcli,
 # kiwoom`cli and "overseas" "orders" still match. Also dropped: the bash backtick, the $ of bash $'...'
 # and $"...", backslashes and backslash-newline escapes, so --con\firm, kiwoom\cli, --con$'f'irm and
-# a --con\<newline>firm continuation match too. This can only add matches.
+# a --con\<newline>firm continuation match too. The quote-only strip is checked as well, so a boundary
+# that only the wider strip removes cannot hide a match: this can only add matches.
+QUOTE_CHARS = re.compile(r"[\"'`^]")
 STRIP_CHARS = re.compile(r"\\\r?\n|[\"'`^\\]|\$(?=[\"'])")
 TRUE_TEXT = {"true", "1", "yes", "y", "on"}
 
@@ -56,7 +58,7 @@ def target_kind(tool_name):
 
 
 def find_marker(text):
-    for variant in (text, STRIP_CHARS.sub("", text)):
+    for variant in (text, QUOTE_CHARS.sub("", text), STRIP_CHARS.sub("", text)):
         for label, pattern in MARKERS:
             if pattern.search(variant):
                 return label
```

`QUOTE_CHARS` 확인(Python): 패턴 문자열이 fix1 전 `STRIP_CHARS`와 같다(`'[\\"\'`^]'`). ASCII 0~127 가운데 걸리는 글자는 `"` `'` `^` 백틱 4개뿐이다. fix1 전 훅은 fix1 사본에서 fix1 diff(위 192~218행)를 거꾸로 적용해 다시 만들었다. 그 sha256이 1차 Judge가 본 ef29c530f47871d2a7e03471229ef68ff38a802285e367d04f334e83be87ebfc(5546바이트)와 같다.

## F7 테스트 변경
- 거짓 음성 변형 목록을 시험 함수 안 튜플에서 모듈 상수 `FALSE_NEGATIVE_VARIANTS`로 옮겼다. 두 시험이 같이 쓰기 위해서다. 기존 23개 문자열은 그대로다(ast로 옛 튜플과 새 튜플 앞 23개가 같음을 확인). 끝에 회귀 사례 2개를 더했다: `"python -m kiwoom_cli domestic orders buy --con\"\"firm$'\\0'"`, `"python -m kiwoom_cli domestic orders buy --con''firm$'\\x00'"`. 값은 셸에 쓰는 글자 그대로(백슬래시 한 개 + `0` / `x00`)이며 ast로 확인했다.
- `TARGET_TOOLS`에 `"Monitor"`를 더하고 `SHELL_FAMILIES = ("Bash", "PowerShell", "Monitor", "device_bash")`를 두었다. 거짓 음성 시험은 이제 4개 도구 모두에서 거절을 확인한다(기존 3개 + Monitor). `test_every_text_marker_is_refused_on_every_target_family`도 `TARGET_TOOLS` 전체를 돌기 때문에 Monitor를 함께 확인하게 됐다. 단언을 더한 것이지 약화한 것이 아니다.
- 새 시험 `test_everything_refused_before_fix1_is_still_refused`: 입력은 `FALSE_NEGATIVE_VARIANTS`, 경계 사례 3개(`--con"firm\-x"`, `--con""firm\<줄바꿈>-x`, `python -c "f(a\con'firm'=True)"`), `TEXT_MARKERS` 값 6개다. 참조 구현 `refused_before_fix1`은 원문과 따옴표만 지운 정리본만 검사한다. 표지 목록은 훅 모듈의 `MARKERS`를 importlib로 읽어 재사용하고, 새 표지는 만들지 않았다. 참조가 거절하는 모든 입력이 4개 셸 도구에서 현재 훅에 거절되는지 subprocess로 확인한다. 시험이 헛돌지 않도록 회귀 2개와 경계 3개가 참조 거절 목록에 들어 있는지도 먼저 단언한다.
- 변이 확인(같은 두 시험을 다른 훅 파일에 돌림): fix1 처음 판에 돌리면 정확히 8건(2×4) + 20건(5×4) = 28건이 실패한다. 거짓 음성 시험에서 회귀 2개 × 4 도구 = 8건, fix1 전 회귀 시험에서 (회귀 2개 + 경계 3개) × 4 도구 = 20건이다(fix3 정정: 처음 문구 "회귀 2개와 경계 3개 × 4 도구 = 28건"은 계산이 틀렸다. fix3 세션에서 fix1 처음 판을 다시 만들어 sha256 375206d7…을 맞춘 뒤 실패한 subTest를 다시 셌다). 재구성한 fix1 전 판에 돌리면 Monitor 줄(fix1 전에는 대상 아님)과 fix1이 새로 잡은 백슬래시 변형 4개에서만 실패한다. 즉 fix1 전 판은 Bash·PowerShell·device_bash에서 회귀 2개와 경계 3개를 모두 거절한다. 현재 판에서는 실패 0이다. 참조 구현과 실제 fix1 전 훅의 판정은 무작위 입력 5만 개에서 모두 같았다.
- 지시문보다 더 한 것(거절 확인만 늘림): Monitor를 `TARGET_TOOLS`에 넣어 텍스트 표지 시험에도 Monitor가 들어간 것, 일반 회귀 시험 입력에 `TEXT_MARKERS` 값을 넣은 것, 헛돌기 방지 단언. 빼려면 `TARGET_TOOLS`의 Monitor 줄과 해당 입력을 지우면 된다.

## 테스트 결과 (이 세션, 2026-10-25)
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_kiwoom_order_block_hook.py"` → Ran 23, OK.
- `-p "test_dev_pipeline*"` → Ran 126, OK. `-p "test_approval_human_check*"` → Ran 28, OK.
- 훅·테스트 파일은 ASCII, CRLF(맨 LF 0)이다. 훅 import는 {json, re, sys} 그대로다(`HookFileShape` 통과).

## 한계 (fix2)
- 합집합 성질은 코드 구조와 무작위 비교로 확인했다. 모든 문자열에 대한 증명은 아니다. 다만 거절 조건이 "변형 중 하나라도"이고 변형 튜플이 두 판의 변형을 모두 담고 있어서, 구조상 줄어들 수 없다.
- 위 "한계"(인코딩된 명령, 변수 이어 붙이기, brace 확장, `$(…)`, `${x}`, 스크립트 파일 실행 등)와 fix1 한계(PowerShell 줄 잇기)는 그대로다. fix2는 회귀만 고쳤다.

## Judge 재확인 항목 대응 (fix2)
| 항목 | 상태 |
|---|---|
| R2 fix1 전 대비 회귀 0, fix1이 잡던 것도 잡음 | 예. 거절 집합 = 두 판의 합집합(결론 3). 회귀 입력 2개와 경계 3개가 4개 셸 도구에서 거절됨 |
| R3 이전 합성 입력(거절·통과) 결과 불변 | 기존 거절·통과 시험이 단언 변경 없이 모두 통과. 거짓 음성 목록은 내용 그대로 옮겼고 Monitor 확인이 더해짐 |
| R6 테스트 전부 통과 | 23 / 126 / 28 OK |
| R1 변경이 F6~F8 범위뿐 | 예. 훅(F6), 테스트(F7), 보고서(F8) 3개 파일. 제안 settings·guard 문서 sha256 불변 |

# fix3 반영 (2026-10-25, 병합 c9c0877 뒤 2차 Judge 수정안 F9~F11)
지시문: docs/claude/kiwoom-block-fix3-prompt.md (출처: 2차 Judge judge-2.txt 108~113행, 원문 workspace/outputs/manual-bj/kiwoom-block/judge-2.txt). 작업 위치는 새 워크트리 `worktree-kiwoom-block-fix3`(기준 main c9c0877, 미커밋)이다. 위의 원래 결론, fix1·fix2 절은 지우지 않았다. 이 보고서에서 고친 곳은 "병합 뒤 확인" 5번, "한계"의 fix3 항목, fix2 절 "F7 테스트 변경"의 변이 확인 문장(28건 계산), 그리고 이 절이다.

## 결론
1. **병합 뒤 실패 3건을 재현했고, 고친 뒤 병합 전·병합 뒤 두 상태에서 모두 통과한다.** 훅·`.claude/settings.json`·deny·제안 settings·guard 문서는 바꾸지 않았다(sha256 아래 표).
2. **단언은 약해지지 않았다.** deny가 줄거나, 임의의 줄이 늘거나, 중복이 생기거나, `hooks`가 빠지면 최소 한 시험이 실패한다(아래 변이 확인).
3. **28건 계산을 다시 셌다.** 8건(2×4) + 20건(5×4) = 28건이 맞다.
4. **F10 우회 계열 7개를 실제로 확인했다.** 현재 훅은 7개 모두 통과시키고, bash에서는 모두 `--confirm`이 된다. 코드 보강은 이번 범위 밖이다(NO_CHANGE, "한계" fix3 항목).

## 재현된 실패 (수정 전, c9c0877 그대로)
- `test_dev_pipeline.StaticScriptTests.test_settings_json_p9`: `AssertionError: 26 != 23`(1496행). `-p "test_dev_pipeline*"` → Ran 126, FAILED (failures=1).
- `test_kiwoom_order_block_hook.ProposedSettingsOnlyAdd.test_added_deny_entries_come_from_the_approved_list`: `0 not greater than or equal to 3`(304행).
- `test_kiwoom_order_block_hook.ProposedSettingsOnlyAdd.test_only_the_hooks_key_is_added_and_other_keys_are_unchanged`: `Items in the second set but not the first: 'hooks'`(313행). `-p "test_kiwoom_order_block_hook.py"` → Ran 23, FAILED (failures=2).
- `-p "test_approval_human_check*"` → Ran 28, OK(영향 없음).

## 바꾼 줄
- `manage-us-stock-strategy/tests/test_dev_pipeline.py`
  - 1225~1226행(새): 주석 1줄과 `KIWOOM_BLOCK_DENY = {"mcp__*__kiwoom_order_preview", "Bash(*overseas orders*)", "PowerShell(*overseas orders*)"}`. 값은 지금 `.claude/settings.json` deny 24~26번째 줄과 글자까지 같다.
  - `test_settings_json_p9`: `assertEqual(len(deny), len(OLD_DENY | P9_DENY))` 한 줄을 다음 세 줄로 바꿨다. `deny = permissions["deny"]`, `assertEqual(len(deny), len(set(deny)))`(중복 없음), `assertIn(set(deny) - (OLD_DENY | P9_DENY), (set(), KIWOOM_BLOCK_DENY))`(추가된 줄은 없음 또는 정확히 그 3줄). 포함 단언 `set(deny) >= OLD_DENY | P9_DENY`와 ask 개수 단언은 그대로다. 그래서 deny는 23줄(병합 전) 또는 26줄(병합 뒤)일 때만 통과한다.
- `manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py`
  - 24~67행(새): `BASE_SETTINGS` 상수. `git show 7f98f28:.claude/settings.json`의 내용을 그대로 옮겼다(deny 23줄·ask 8줄·키 effortLevel/permissions/worktree, 순서 그대로). 이 세션에서 git blob을 JSON으로 읽어 상수와 `==`임을 확인했다. `auto_core.py` 두 줄은 test_dev_pipeline.py의 `OLD_DENY`처럼 `"auto_core" + ".py"`로 나눠 적었다.
  - `ProposedSettingsOnlyAdd.setUpClass`: `cls.current`를 살아 있는 settings.json 대신 `BASE_SETTINGS`로 바꿨다. 기존 6개 시험의 단언은 한 글자도 바꾸지 않았다.
  - 새 시험 `test_live_settings_are_the_base_or_exactly_the_proposed_file`: 실제 `.claude/settings.json`이 제안 파일과 바이트까지 같으면 통과, 아니면 JSON으로 읽은 값이 `BASE_SETTINGS`와 같아야 한다.
  - 새 시험 `test_base_constant_has_the_base_shape`(지시문보다 더 한 것): 상수 자체가 키 3개, permissions 키 {ask, deny}, deny 23줄(중복 없음), ask 8줄인지 확인한다. 상수가 실수로 바뀌는 것을 막는다. 빼려면 이 시험만 지우면 된다.
  - 그래서 훅 테스트 수는 23개에서 25개가 됐다.

## 변이 확인 (스크래치 사본에서만, 실제 파일 수정 0)
스크래치 폴더에 settings 사본을 만들고 테스트 모듈의 경로 상수(`test_dev_pipeline.ROOT`, 훅 테스트의 `CURRENT_SETTINGS`·`PROPOSED_SETTINGS`)만 사본으로 돌려 `test_settings_json_p9`와 `ProposedSettingsOnlyAdd` 8개를 돌렸다. 기준 사본은 git blob(LF)을 체크아웃 형태(CRLF)로 바꾼 것이고, sha256 f793271f…(1384바이트)가 위 155행의 병합 전 값과 같다.
| 상태 | p9 | ProposedSettingsOnlyAdd에서 실패한 시험 |
|---|---|---|
| 실제=기준(병합 전) | 통과 | 없음 |
| 실제=제안 파일(병합 뒤) | 통과 | 없음 |
| 실제에서 deny 한 줄 삭제(`Read(./.env)`) | 실패 | live_settings |
| 실제에서 키움 deny 한 줄 삭제(`Bash(*overseas orders*)`) | 실패 | live_settings |
| 실제에 이상한 deny 한 줄 추가(`Bash(*harmless-extra*)`) | 실패 | live_settings |
| 실제에 deny 중복 한 줄 | 실패 | live_settings |
| 실제에서 `hooks` 삭제 | 통과(p9는 hooks를 보지 않음) | live_settings |
| 제안 파일에서 deny 한 줄 삭제 (실제=기준 / 실제=같은 사본) | 통과 / 실패 | added_deny, existing_deny_and_ask (두 경우 모두) |
| 제안 파일에서 키움 deny 삭제 / 이상한 줄 추가 / 중복 (같은 두 경우) | 통과 / 실패 | added_deny (모든 경우) |
| 제안 파일에서 `hooks` 삭제 (같은 두 경우) | 통과 / 통과 | hook_entry, only_the_hooks_key (두 경우 모두) |

모든 변이가 최소 한 시험에서 실패한다. `hooks` 삭제는 p9가 아니라 훅 테스트가 잡는다(p9는 원래 dev 파이프라인 권한 줄만 본다).

## 28건 재계산 (F11)
현재 훅에서 F6 diff(위 340~359행)를 거꾸로 적용해 fix1 처음 판을 다시 만들었다. sha256 375206d7…(5793바이트)가 위 154행 값과 같다. 그 파일에 거짓 음성 시험과 fix1 전 회귀 시험을 돌렸다. 실패한 subTest는 `test_false_negative_variants_are_still_refused` 8건(글자열 2개), `test_everything_refused_before_fix1_is_still_refused` 20건(글자열 5개), 합계 28건이다.

## 테스트 결과 (이 세션, 2026-10-25, 수정 뒤, 워크트리 = c9c0877 + fix3)
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_kiwoom_order_block_hook.py"` → Ran 25, OK.
- `-p "test_dev_pipeline*"` → Ran 126, OK. `-p "test_approval_human_check*"` → Ran 28, OK.
- 새 실패 0, skip 0. 병합 전 상태(실제=기준)는 위 변이 확인 첫 줄로 확인했다.
- 두 테스트 파일은 CRLF(맨 LF 0)다. 훅 테스트는 ASCII다. test_dev_pipeline.py는 원래 비ASCII 바이트 271개(한글 문자열)가 있었고 fix3 뒤에도 271개다. 더한 줄은 모두 ASCII다.

## 파일 sha256 (CRLF 그대로)
| 파일 | fix3 전 (c9c0877 체크아웃) | fix3 뒤 |
|---|---|---|
| manage-us-stock-strategy/tests/test_dev_pipeline.py | 5e113544c249284cb1cc147899fa36d822409216d19a651795b4255150b490eb (96940) | eff5db3ac07e04e263095ec3d6a1133f7500c0499d3bd3b8389c8bce7ba3ac61 (97262) |
| manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py | 859b57e8d91cb8f18fa6353252021f893d580c37af40a7e409cc4fcfb8f5a30b (19507) | 87c055b7d9c651239e359def8bb2e752c032425560c02dc26c300a588a9f0f5f (22208) |
| docs/claude/kiwoom-block-builder-report.md | 58bd0cef162f23187c260edde869f985338696a1283125688a9c82b83492964b (52065) | (자기 자신은 적을 수 없음 — docs/claude/kiwoom-block-fix3-report.md에 적음) |
| .claude/settings.json | 459cd04f0dee5aa915fafc0397af2369b9348aab19632505df953d466ea36942 (1952) | 변경 없음 |
| .claude/hooks/kiwoom_order_block.py | 2818d79fcdd5ee2083be65c888447ea84a04f75188ca35376a5b2038c87cc81f (5971) | 변경 없음 |
| docs/claude/kiwoom-block-settings-proposed.json | 459cd04f…(위 settings와 같음) | 변경 없음 |

## 하지 않은 것 (fix3)
훅·`.claude/settings.json`·deny·제안 settings·guard 문서·CLAUDE.md·tools/**·키움 패키지 수정 0건. 키움 도구·CLI 실행 0건. 비밀 접근 0건. 커밋·push·병합 0건. 우회 계열 코드 보강 0건(NO_CHANGE). docs/claude/_pending 파일과 관제판 갱신은 허용 파일 밖이라 하지 않았다. BLOCKED.md 없음.
