# wtwarn-1127 Judge A 보고서 (병합 전)

base: 26d5a79b47d0600a73128d695fa012e3ed6209cd

- 검토: 2026-11-28 15:00~15:50 KST, 데스크톱 Claude Code 새 세션(Worktree 끔, 메인 체크아웃 `E:\사업\##금동한\코덱스저장소`, 맨 위 CLAUDE.md 있음), Opus 5.5. Builder와 다른 세션. 지시: `docs/claude/wtwarn-1127-judge-prompt.md` A절.
- 대상: Builder worktree `E:\사업\##금동한\코덱스저장소\.claude\worktrees\wtwarn-1127`(브랜치 `worktree-wtwarn-1127`, HEAD 26d5a79 = 메인 브랜치 `codex/master-recovery-expansion` HEAD)의 미커밋 변경 6개와 `docs/claude/wtwarn-1127-builder-report.md`.
- 검토 대상 파일은 고치지 않았다. Builder worktree에서는 아무것도 실행하지 않았고, 훅·테스트는 모두 임시 폴더의 바이트 같은 사본으로 돌렸다.

## merge-sha256
85c9b089d752e96371e4f5f925641f38964cece9e18f23efa1a7cb9be65bf131  .claude/hooks/worktree_base_warn.py
17b05bbb8613ba2830cdb0beaff510f856f8748d20140d09c3bd3e5ded273def  manage-us-stock-strategy/tests/test_worktree_base_warn_hook.py
19869c6e98eb96de07a6d40fd263ce0fb28934e5e2310d8c08c7f7df5ed0dc11  manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py
c341b871a6e0ca473e9ae0d0d1c8fa4c221c359e50e7b1d3c060740015c96a71  docs/claude/wtwarn-1127-settings-proposed.json
c649341f8561f7753c54bc161592810907c710d6067f063188ae1d99e3e8bda6  docs/claude/wtwarn-1127-builder-report.md
05034ea6be867a5de9b233bfd3cd0e13cde507a569232de0a0da321b192fab32  docs/claude/wtwarn-1127-merge.ps1
f64299c20a5651b6c64d849b90dc712fb52ae12154a72944929ea704b9a7d3be  docs/claude/wtwarn-1127-design.md
8d7302a088534bac7a3418e57ac9b4393bca1a01294e989aae844d74d2033b13  docs/claude/wtwarn-1127-builder-prompt.md
99aa1ab15335a7602953ca630bbcb6d1006ebefc0532eca75c3bf79dfd764585  docs/claude/wtwarn-1127-judge-prompt.md
## 1. 결론

**PASS.** 10개 항목 모두 PASS다. 막는 결함·고칠 것은 없고, 참고 사항 4건(5절)은 모두 비차단이다(멈추는 쪽으로만 틀리거나, 설계 2-6이 이미 받아들인 한계와 같은 부류).

위 해시는 이 세션이 Python `hashlib`로 직접 계산한 값이다(Builder 6개는 worktree 원본, 설계 문서 3개는 메인 사본. 설계 문서 3개는 worktree 사본과도 바이트가 같다). Builder 보고서 1절·7절의 해시와도 같다.

## 2. 항목별 판정

| # | 판정 | 근거 |
|---|---|---|
| A1 허용 파일 | PASS | `git --no-optional-locks -C <wt> status --porcelain --untracked-files=all` = `M` kiwoom 테스트 1개 + `??` 5개(훅·새 테스트·제안 settings·병합 스크립트·Builder 보고서). 모두 `wtwarn-1127-builder-prompt.md:8` allowed_files 안. `.claude/settings.json`·CLAUDE.md·AGENTS.md·tools/** 변경 0. 무시 파일인 worktree `.claude/settings.local.json`도 메인과 바이트 같고 수정 시각 2026-10-05. kiwoom 테스트 diff는 한 덩어리 `@@ -346,6 +346,20 @@`, +14줄·−0줄, 모두 `test_live_settings_are_the_base_or_exactly_the_proposed_file` 안(worktree `test_kiwoom_order_block_hook.py:349-362`): 함수 지역 bytes `block` 1개와, `raw.count(block) == 1 and raw.replace(block, b"") == PROPOSED_SETTINGS.read_bytes()`이면 return하는 통과 상태 1개. 마지막 `assertEqual(..., BASE_SETTINGS)`와 다른 단언·모듈 상수·import 변경 0. worktree 맨 위 CLAUDE.md 있음, `merge-base --is-ancestor codex/master-recovery-expansion HEAD` 종료 0(HEAD 26d5a79). |
| A2 settings | PASS | `git diff --no-index <메인>/.claude/settings.json <wt>/docs/claude/wtwarn-1127-settings-proposed.json` = `@@ -43,0 +44,11 @@`, `+` 11줄·`-` 0줄(제안 파일 44-54행). 제안 파일에서 끼운 11줄(바이트)을 빼면 메인 settings.json(sha256 459cd04f…)과 바이트가 같다 → `permissions.ask`·`permissions.deny`·`hooks.PreToolUse`·`worktree.baseRef`·`effortLevel` 바이트 동일(파싱 비교도 같음). JSON 유효. `SessionStart` = `[{"hooks":[{"type":"command","command":"python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/worktree_base_warn.py\"","timeout":10}]}]` — matcher·onFailure 없음. 70줄 모두 CRLF, 끝 CRLF 1개. `permissions` 객체 전체가 같고 `allow` 없음. |
| A3 훅 제한 | PASS | AST 검사(이 세션 스크립트): import = {json, os, re, sys}(`worktree_base_warn.py:9-12`). `open`·`subprocess`·`socket`·`eval`·`exec`·`compile`·`__import__`·`input`·`getcwd`·`print`·`stderr`·`getenv` 등 이름·속성 0. `os` 사용 = `os.path.{abspath,dirname,exists,isdir,isfile,join,normcase}`·`os.environ.get`·`os.name`·`os._exit`뿐. 환경변수는 `os.environ.get("CLAUDE_PROJECT_DIR")` 1곳(:64). `os.getcwd()` 호출 0. stdout은 `json.dumps(..., ensure_ascii=True)` 1번(:100-102, :107-110), `.format`·f-string 0. `run()`(:105-117) = `try/except BaseException` → flush를 `try`로 한 번 더 → 마지막 문장 `os._exit(0)`. 모듈 최상위는 docstring·import·상수·함수·`__main__` 가드뿐. 아래 A4의 모든 실행에서 종료 0·stderr 0바이트·stdout은 0바이트 또는 ASCII JSON 1개. |
| A4 판정 직접 시도 | PASS | 임시 폴더(`%TEMP%\wtj-*`, 그 아래 `사업\##금동한\코덱스저장소` 꼴 가짜 메인, 훅은 그 안의 바이트 같은 사본)에서 합성 입력 102건, 거짓 경고 0·놓침 0. 경고 출력은 설계 3절 원문을 이 세션이 직접 채운 문자열과 **전체 글자가 같은지** 비교했다. 정상→조용: 메인(`.git` 폴더+CLAUDE.md) 맨 위·하위, 새 worktree(`.git` 파일+CLAUDE.md) 맨 위·`sub/dir`, 새 클론. 옛→경고: 옛 worktree(`.git` 파일, CLAUDE.md 없음) 맨 위·`sub/dir`, 옛 클론(`.git` 폴더), CLAUDE.md가 폴더인 경우. source 5종은 그 값, 없음·`weird`·5·빈 값·`STARTUP`·배열·객체는 `unknown`. 깨진 입력 21종(빈 값, JSON 아님, `[]`, `null`, `true`, 문자열, 숫자, `cwd` 숫자·빈 문자열·null·배열·객체·없음, `{}`, 잘못된 UTF-8(본문·값 안), UTF-16, 잘린 JSON, 뒤에 쓰레기, NUL, 1MB 초과) → 조용. 1,048,576바이트 유효 입력은 경고, 1,048,577바이트는 조용(경계 정확). BOM+옛은 경고, BOM+새는 조용. 없는 경로·파일 경로·`.git` 조상 없는 임시 폴더(전제 단언 통과) → 조용. `/c/…` 꼴 cwd(옛 맨 위·하위 경고, 새·새 하위·메인 조용, 대문자 드라이브도 같음), `/c/…` 꼴 `CLAUDE_PROJECT_DIR` → 메인 CLAUDE.md 절대 경로가 들어감. `CLAUDE_PROJECT_DIR` 없음·빈 값·root와 같음(직접·`/x/` 꼴)·CLAUDE.md 없음·없는 경로·파일 → `FALLBACK_MAIN`. 끝 역슬래시·끝 슬래시·섞인 구분자·대소문자 차이, `\\?\` 접두(옛 경고, 새·새 하위 조용), UNC `\\localhost\C$\…`와 `\\?\UNC\…`(옛 경고, 새 조용 — 이 PC에서 관리 공유 접근 가능 확인). 깊이: `.git`에서 63단계 아래 시작은 경고, 64·65·66단계는 조용(설계 2-2의 '64단계 안' 판정 불가), 새 root 66단계 아래 조용. 경로에 `{root}`·`{main_claude}`·`{source}`·`{}`·한국어·`##` → 다시 채워지지 않고 그대로 표시. 200자 넘는 root·메인 경로 → `…`+끝 199자, 문맥 1,110자. stdin 없음 → 조용·종료 0, stdout 닫힘(`>&-`) → 종료 0·stderr 0. **실제 worktree 전수(읽기만, 존재 확인)**: `git worktree list` 203개 중 폴더 없는 `/tmp/wt` 1개 제외 202개에 실제 메인을 `CLAUDE_PROJECT_DIR`로 두고 돌림 → 경고 47개(모두 HEAD 41f7b3f, 맨 위 CLAUDE.md 없음 — 설계 F5의 47개와 같음, 문맥에 `E:\사업\##금동한\코덱스저장소\CLAUDE.md` 들어감), 조용 155개(모두 CLAUDE.md 있음). 거짓 경고 0·놓침 0. |
| A5 경고문 | PASS | `CONTEXT_TEMPLATE`·`SYSTEM_MESSAGE`·`FALLBACK_MAIN`이 설계 3절(`wtwarn-1127-design.md:104-118`, 102행)과 글자 같다(`{decided}` → `2026-11-27`; 설계 머리 `status`(design.md:4) "2026-11-27 16:06 KST … {decided} = 2026-11-27"과 같음). 차이 줄 0. 자리 3개 각 1번, `{decided}` 자리 없음. 자리 뺀 길이 703자(≤ 1,100), 최악 채움 703 + 7 + 200 + 200 = 1,110자(≤ 1,500, 실측 1,110), systemMessage 153자(≤ 200). 문장은 "사실: …", "사장 결정(…): … 한다/하지 않는다"의 사실·결정문이다. "절대 경로로 고치는 것도 하지 않는다", "현재 규칙을 읽은 뒤에도 같다"(:19)로 세 가지 금지 독해를 막고, 새 세션 안내는 "Worktree 끔 / 기준 브랜치 codex/master-recovery-expansion"(:20, :24)뿐이라 main으로 커밋·PR·병합으로 읽힐 문장이 없다. |
| A6 테스트 | PASS | 아래 3절 표. (가) 병합 전 상태(worktree와 바이트 같은 임시 사본) 새 테스트 20 OK, kiwoom 25 OK. (나) 병합 뒤 상태(같은 사본 + `.claude/settings.json` 자리에 wtwarn 제안 파일 c341b871…) 새 테스트 20 OK, kiwoom 25 OK. skip 0. 새 테스트에 `skip`·`expectedFailure` 0. 기준선(26d5a79, kiwoom 원본) 대비 새 실패 0: `test_dev_pipeline*` 209개 중 실패 1개 `test_repository_switch_is_off`(`test_dev_pipeline_api_route.py:259`, 2026-11-25 사장 승인으로 켜진 저장소 스위치 값 — 기준선부터 같은 실패, 이 작업과 무관), `test_approval_human_check*` 28 OK. 원래 kiwoom 테스트를 병합 뒤 상태에 두면 실패 1개(통과 상태 추가가 필요함 확인). 시간 테스트 상한은 중앙값 < 1.0초·각 < 5.0초(`test_worktree_base_warn_hook.py:243-252`). |
| A7 시간 | PASS | old-x 꼴 입력, 직접 10회: 0.042·0.042·0.042·0.043·0.040·0.041·0.040·0.041·0.042·0.042초(최대 0.043). Git Bash(`C:\Program Files\Git\bin\bash.exe`) 경유, settings 명령 그대로 `bash -c 'python "${CLAUDE_PROJECT_DIR}/.claude/hooks/worktree_base_warn.py"'`(`CLAUDE_PROJECT_DIR` = `##`·한국어가 든 가짜 메인) 3회: 0.105·0.095·0.095초. 모두 1.0초 미만. |
| A8 병합 스크립트 | PASS | 실행하지 않고 읽고, PS 5.1(5.1.26100) 파서로만 확인(오류 0). ASCII(비ASCII 줄 0)·CRLF 314줄. 경로는 `$PSScriptRoot` 상대(`wtwarn-1127-merge.ps1:46-50`). 읽는 git은 모두 `--no-optional-locks`(:85 `Git-Read`, :120, :163, :311); 쓰는 git은 메인의 reset·add·commit(:244, :284, :288)뿐. 확인 1 콘솔(:13-43) → 2 `Test-Windows`(:96-111) → 3 브랜치·기준(:114-124) → 4 Judge 보고서 `VERDICT: PASS`·`base:`·`## merge-sha256` 9경로 정확히 1번씩, 중복·목록 밖 경로도 멈춤(:127-158) → 5 메인 상태(:161-173) → 6 worktree 변경 집합 = 복사 목록(:176-177) → 7 ref·runtime(:180-188) → 8 훅 시험(:191-224)을 모두 바꾸기 전에 하고, 두 번째 `Test-Windows`(:227) 뒤 `Test-MainState`(새 경로 부재·settings sha·kiwoom=기준)·`Test-ReviewedFiles`를 다시 하고 보관 바이트 sha256을 확인(:228-236). 복사(:255-271) → 복사본 해시 = Judge 해시(:272-275) → 메인 사본 테스트 2개(:276-283) → `git add -- <7경로>`·스테이지 집합 확인(:284-287) → 경로 지정 커밋 1개(:288-291). 커밋 전 어느 실패에도 `Undo-Copy`, 중단에는 finally(:293-295)가 `Restore-Main`(:243-252)을 부른다: 먼저 `git reset -q -- <경로들>` → settings·kiwoom을 보관 바이트로 → 복사에 성공한 새 경로(`$created`, :261)만 삭제 → 남으면 `ROLLBACK_INCOMPLETE`. 해시 상수는 지시문 ④-5가 정한 기준 settings sha(:55)뿐이고 검토 파일은 Judge 해시 목록을 기준으로 본다. Judge 보고서는 복사·커밋 목록에 없음(:63-73). 바꾼 뒤 확인·되돌리기 줄(:297-314). push·`update-ref`·`checkout`·`-ApproveAuthority`·dev-run/merge/queue 실행 0(grep; `Push-Location`만 걸림). 이 세션의 보조 확인: PS 5.1은 네이티브 명령에 `--`를 그대로 넘김(배열 변수 뒤 포함), `git reset -q -- <스테이지된 경로 + 미추적·없는 경로>`는 종료 0으로 스테이지만 풂(임시 저장소), PS 5.1에서 실행 중지(Stop — Ctrl+C와 같은 경로) 때 finally의 되돌리기·`Write-Output` 뒤 줄까지 모두 실행됨(임시 폴더 시험). |
| A9 연결표 ②③⑤ 원문 대조 | PASS | hooks 문서 원문(code.claude.com/docs/en/hooks, 2026-11-28 15:3x KST 내장 브라우저): 'Add context for Claude' 절의 "SessionStart and SubagentStart: at the start of the conversation, before the first prompt", 종료 코드 표 SessionStart 행 "Shows stderr to user only", 공통 JSON 필드 systemMessage "Warning message shown to the user", "Claude Code saves the injected text in the session transcript" — 4개 모두 글자 그대로 있음(그 밖에 matcher 값 5종, "omit the matcher … activates on every occurrence", command 기본 timeout 600, 10,000자 상한, "factual statements rather than imperative" 확인). settings 행 예정값 44-54 = 제안 파일 44-54행(A2). `dev-dashboard-protocol.md:36-41` = 결정 작업 필드 ask·default·answerHint(`결정 <작업 id>: `)·deadline(기한 지나면 default 기록 뒤 닫음), `:45-47` = status waiting·'재개 가능' 계산·resume.type date. `CLAUDE.md:138` = Default disposition "Ask the user only when the result proposes a change". 설계 6절(2단계 가드 답 없으면 NO_CHANGE)·7절(집계 방법·기준)·9절 2·7(색인·관제판 wtwarn-p2)이 표 칸과 맞는다. 색인 `active-decisions.md:196-197`에 wtwarn-1127·wtwarn-p2 행이 이미 있다(메인 작업 폴더, 미커밋). |
| A10 권한·접근 | PASS | 새 파일들에 허용·한도·권한 확대 표현 0(경고문은 금지·안내만). Builder 세션 기록 2개(`~/.claude/projects/E-------------------claude-worktrees-wtwarn-1127/3ef4c64b….jsonl`, `0a3f77b5….jsonl`) 전수: 도구는 Bash·PowerShell·Read·Glob·Write·Edit뿐, 키움·MCP 도구 호출 0, `.env`·토큰 읽기 0, git commit·push 0. Write/Edit 대상은 허용 파일 4개와 Builder 자기 scratchpad뿐. 2026-11-28 `git merge --ff-only codex/master-recovery-expansion`(worktree 브랜치만)은 같은 기록의 사장 입력(2026-11-28 05:59:13Z = 14:59 KST "이 worktree 브랜치만 git merge --ff-only … 메인·main·runtime은 건드리지 않음")을 따른 것. CLAUDE.md 복사·생성 0(CLAUDE.md 없는 worktree 수 47 = 설계 F5). user-global `~/.claude/settings.json`에 wtwarn·worktree_base_warn 참조 0. `main` = 41f7b3f…, `origin/HEAD` → `refs/remotes/origin/main` = d574379…, runtime HEAD 41f7b3f·깨끗함, 메인 스테이지 0·대상 경로 깨끗함(이 세션 확인). |

## 3. 테스트 (임시 사본, `python -B -m unittest discover -s manage-us-stock-strategy/tests -p <패턴>`, `PYTHONDONTWRITEBYTECODE=1`)

사본 만드는 법: Builder worktree의 추적 파일 2,669개를 그대로 복사 → `base`(kiwoom 테스트만 `git cat-file --filters HEAD:` = 메인 사본 sha 87c055b7…, 새 파일 없음), `pre`(worktree와 같음 — 바뀐 7경로 sha 대조), `post`(`pre` + `.claude/settings.json` = wtwarn 제안 파일), `post_oldkiwoom`(`post` + 원래 kiwoom 테스트).

| 상태 | worktree_base_warn | kiwoom_order_block | dev_pipeline* | approval_human_check* |
|---|---|---|---|---|
| base(26d5a79) | — | 25 OK | 209, 실패 1 `test_repository_switch_is_off` | 28 OK |
| pre(병합 전) | 20 OK | 25 OK | 209, 실패 1 같은 이름 | 28 OK |
| post(병합 뒤) | 20 OK | 25 OK | 209, 실패 1 같은 이름 | 28 OK |
| post_oldkiwoom | — | 25, 실패 1 `test_live_settings_are_the_base_or_exactly_the_proposed_file`(예상대로 — 더한 통과 상태가 필요함) | — | — |

## 4. 하지 않은 것
검토 대상 파일 수정, Builder worktree 안에서의 실행, 커밋·push, dev-run·dev-merge·dev-queue·auto_core·apply, 병합 스크립트 실행, 키움 도구·CLI, 비밀 읽기, `main`·runtime worktree·origin/HEAD 변경, 관제판 갱신(Judge는 하지 않음). 쓴 것은 이 보고서와 `docs/claude/_pending/wtwarn-1127-judge-a.txt`뿐이다.

## 5. 참고 (비차단 — 이번 병합을 막지 않음)
1. 병합 스크립트 확인 3(`wtwarn-1127-merge.ps1:122-124`): git은 기본 설정(`core.quotepath` 미설정)에서 한글 경로를 `"docs/claude/\353…"`처럼 따옴표로 싸서 출력한다. 기준 26d5a79 뒤에 한글 이름의 docs/claude 파일이 메인에 커밋되면 'main changed outside docs/claude'로 **잘못 멈춘다**(아무것도 바꾸지 않음 — 멈추는 쪽으로만 틀림). 지금은 기준 = 메인 HEAD이고 `_pending`에 한글 경로가 없어 해당 없음. 멈추면 그 메시지가 경로를 보여 주므로, 그때 worktree 앞으로 감기와 같은 절차로 다시 받는다.
2. 메인 체크아웃 안에 `.claude/worktrees` 밖의 중첩 git 폴더가 6개 있다(`.runtime-cache\kiwoom-mcp-20260928`, `.runtime-cache\uv-cache\sdists-v9`, `.runtime-cache\kiwoom-spec\uv-cache\sdists-v9`, `workspace\outputs\activation\…\isolated-runtime` 3개, 모두 CLAUDE.md 없음). 메인에서 연 정상 세션의 셸 위치가 이 안으로 옮겨진 채 `/clear`·압축·재개가 일어나면 거짓 경고가 뜬다. 설계 2-6 셋째 줄(정상 세션이 옛 worktree로 `cd`한 채 압축)과 같은 부류이고, 결과는 그 세션이 수정을 멈추고 새 세션을 권하는 것뿐이다(권한·주문 영향 없음). 설계 7절 집계 때 이 경로의 발동이 있으면 함께 본다.
3. 상대 경로나 드라이브 없는 POSIX 꼴(`.`, `/tmp/x`) `cwd`는 `os.path.abspath`가 훅 프로세스 폴더(메인)·드라이브 기준으로 푼다. Claude Code는 절대 경로를 보내고, 이 경우에도 결과는 조용함(메인에 CLAUDE.md 있음) 쪽이다.
4. `/x`(드라이브만)를 `X:/`로 바꾸는 것은 지시문 ①-2(`X:` + 나머지)와 나머지가 빈 경우만 다르다(Builder 보고서 8절). `X:`는 그 드라이브의 현재 폴더라는 뜻이 되므로 Builder 쪽이 맞다.

## 6. 검토 완결
원문 확인 10/10(A1~A10 근거 모두 이 세션에서 직접 열거나 실행) · 자료 시점 2026-11-28 15:00~15:50 KST · 바뀔 조건: 9개 파일 중 하나라도 위 해시와 달라지면 이 판정은 무효(병합 스크립트가 멈춤), 메인이 26d5a79 뒤로 docs/claude 밖을 바꾸면 Builder 기준 갱신 뒤 다시 Judge A.

사장께:
결론 PASS — 경고 훅·제안 settings·테스트·병합 스크립트 모두 지시문대로이고, 직접 시험 102건과 실제 worktree 202개에서 거짓 경고·놓침이 0이었습니다.
병합은 사장 PowerShell 한 줄입니다(화~토 05:45–09:00, 매일 23:05–23:45 KST 밖): `& 'E:\사업\##금동한\코덱스저장소\.claude\worktrees\wtwarn-1127\docs\claude\wtwarn-1127-merge.ps1'`
병합 뒤에는 이 지시문 B절(실제 세션 점검)을 새 세션(Worktree 끔)으로 시작하면 됩니다.
VERDICT: PASS
