---
id: wtwarn-1127-design
type: design
status: "승인됨 — 2026-11-27 16:06 KST(07:06Z 무렵), 사장이 이 설계 세션(local_f630e826)에 직접 입력한 '1번, 이대로 승인'. 경고문 {decided} = 2026-11-27. 다음: 9절 2(메인으로 옮기기·색인·관제판) → Builder"
as_of: 2026-11-27
tickers: []
evidence: "저장소 git·파일 읽기, 옛 세션 기록 1건, Claude Code 문서 원문(브라우저) — 1절 표"
consumers: "Builder(docs/claude/wtwarn-1127-builder-prompt.md) · Judge(docs/claude/wtwarn-1127-judge-prompt.md) · 옛 기준 worktree에서 열리는 Claude 세션(훅 출력) · 병합 + 14일 2단계 판정 세션(7절)"
summary: "데스크톱 앱이 옛 로컬 main(41f7b3f, 2026-08-15)에서 잘라 CLAUDE.md가 없는 worktree에서 세션이 열리거나 다시 열리면, SessionStart 훅이 짧은 한국어 경고를 Claude 문맥과 사장 화면에 띄운다. 막지 않는다. 2단계 차단 가드는 2주 뒤 결정(기본 NO_CHANGE)."
class: "일반 변경 · 개발 큐 보호 경로(.claude/**)라 수동 경로: Builder(claude --worktree, Opus) → 별도 읽기 전용 Judge(Opus, Worktree 끔) → 사장 PowerShell 한 줄 병합 → 병합 뒤 실제 세션 점검"
authority: "order_authority=false · quantity_authority=none · 키움 호출 0 · 정책·상태·일지·원장·등록부 쓰기 0 · deny/ask 완화 0 · main·runtime worktree·origin/HEAD 변경 0"
source_decision: "사장 2026-11-27 '추천대로 진행'(4단계 계획 승인 — 부모 세션 local_df2d6847이 전달, 이 세션에서 원문 미확인). 이 설계 자체의 승인: 2026-11-27 16:06 KST 이 세션 사장 직접 입력 '1번, 이대로 승인'(추천 1 '이대로 승인' 선택)."
location_note: "이 문서·Builder·Judge 지시문은 지금 설계 세션 worktree(.claude/worktrees/warn-hook-design-7a5628, 브랜치 claude/warn-hook-design-7a5628, 기준 ea3763f)에만 미커밋으로 있다. 이 세션에서 메인 체크아웃 쓰기는 앱이 막았다(2026-11-27 15:0x KST Write 거절). 승인 뒤 9절 2의 세션이 세 파일을 메인 docs/claude에 같은 바이트로 옮기고 _pending으로 커밋한다 — 그 뒤로는 메인 사본이 원본이다."
---

# wtwarn-1127 — 옛 기준 worktree 경고 훅 (SessionStart) 설계

## 0. 결론 먼저
1. 새 SessionStart 훅 1개(`.claude/hooks/worktree_base_warn.py`). 세션이 시작·재개·`/clear`·압축·분기될 때 작업 폴더 맨 위에 `CLAUDE.md`가 없으면 경고를 낸다: Claude 문맥에 1,500자 이하, 사장 화면에 한 줄. 있으면 아무것도 내지 않는다. 세션을 막지 않는다.
2. 바뀌는 것: 새 파일 2개(훅·테스트)와 `.claude/settings.json`의 `hooks` 안에 `SessionStart` 줄 **끼워 넣기만**. `permissions.ask/deny`, 기존 주문 차단 PreToolUse 항목, `worktree.baseRef`는 한 바이트도 안 바뀐다. 그리고 기존 주문 차단 테스트 1곳(`test_kiwoom_order_block_hook.py:344-349`)에 '허용되는 라이브 settings 상태' 1개를 더한다 — 지금 그 테스트는 라이브 settings가 kiwoom 제안 파일과 바이트가 같을 때만 통과해서, 이 병합 뒤 반드시 실패한다. 주문 차단 규칙·다른 단언은 그대로다.
3. 경로: `.claude/**`는 개발 큐 보호 경로라 수동 경로(CLAUDE.md:150-154). 설정은 제안 파일 + 사장 PowerShell 한 줄(선례 9c32545 kiwoom-block, 병합 스크립트 틀은 최신 policy-a-merge-2026-11-27.ps1).
4. 2단계 차단 가드(CLAUDE.md 없는 worktree에서 Edit/Write/커밋 거절)는 이번 범위 밖. 병합 뒤 14일 발동 기록으로 판단, 기본 NO_CHANGE(7절).

## 1. 확인한 사실 (2026-11-27 KST, 이 세션에서 직접 읽음)

| # | 사실 | 값 | 출처(이 세션에서 연 것) |
|---|---|---|---|
| F1 | 이 설계 세션 위치 | worktree 맨 위에 CLAUDE.md 있음. `git merge-base --is-ancestor codex/master-recovery-expansion HEAD` 성공(HEAD = ea3763f = 그 브랜치) | git, 14:47 KST |
| F2 | 로컬 main | `41f7b3f821a4…`, 2026-08-15 15:07 +0900. `41f7b3f..codex/master-recovery-expansion` = 926커밋 | `git rev-parse main`, `git rev-list --count` |
| F3 | origin/HEAD | `refs/remotes/origin/HEAD` → `refs/remotes/origin/main` = `d574379…`(2026-08-14). 이 커밋에도 CLAUDE.md 없음 | `git symbolic-ref`, `git cat-file -e` |
| F4 | 옛 트리 | 41f7b3f 트리에 CLAUDE.md·CLAUDE.local.md 없음, `.claude/` 폴더도 없음 | `git ls-tree -r 41f7b3f` |
| F5 | worktree 수 | 연결된 worktree 201개(`git worktree list` 202줄 − 메인). 맨 위에 CLAUDE.md 없는 것 47개, 모두 41f7b3f: `claude/*` 46개 + runtime `E:\사업\##금동한\runtime\stock-strategy-scheduled`(브랜치 main) | `git worktree list --porcelain` + 폴더별 파일 확인 |
| F6 | 옛 세션에서도 훅은 메인 쪽에서 돈다 | `dazzling-moore-78f859`(41f7b3f) 세션 기록 2026-11-20 07:56~08:14Z, cwd = 그 worktree, Claude Code 2.1.326. 기록에 `kiwoom_order_block: refused - Bash: order marker '/api/us/ordr'` 3회. 그 worktree의 `.claude/hooks/`에는 `__pycache__`만 있고 훅 .py가 없음 → 훅 스크립트는 메인 체크아웃 것이 실행됨. 같은 기록의 cwd 값에는 `E:\…`꼴과 `/e/…`꼴이 섞여 있음 | `~/.claude/projects/E-…-dazzling-moore-78f859/6c083c25….jsonl` grep, 폴더 목록 |
| F7 | 문서: 데스크톱 worktree 세션 | "reads project configuration such as settings, hooks … from the main checkout's root. Hook commands run in that root, and ${CLAUDE_PROJECT_DIR} points at it. … read the worktree's path from the hook's cwd input field. CLAUDE.md files and .claude/rules/ still load from the worktree." | code.claude.com/docs/en/worktrees, 14:58 KST 브라우저 원문 |
| F8 | 문서: SessionStart | matcher 값 `startup`·`resume`·`clear`·`compact`·`fork`. command·mcp_tool 훅만. 평문 stdout 또는 JSON `hookSpecificOutput.additionalContext`가 문맥에 들어감. additionalContext는 "doesn't appear as a chat message in the interface". 종료 코드 표: SessionStart는 막지 못하고 "Shows stderr to user only". 문자열 상한 10,000자(넘으면 파일로 빼고 앞 2,000자만). command 훅 기본 timeout 600초. "Write the text as factual statements rather than imperative system instructions"(명령조는 프롬프트 주입 방어에 걸려 사장에게 그대로 보여질 수 있음). 주입 문맥은 세션 기록에 저장됨. `systemMessage` = "Warning message shown to the user". stdout에는 JSON 객체만 | code.claude.com/docs/en/hooks, 14:52~14:57 KST 브라우저 원문 |
| F9 | 문서: CLAUDE.md·AGENTS.md | CLAUDE.md는 cwd와 "every directory above it"에서 읽는다. AGENTS.md는 "only when you have no CLAUDE.md in your working directory or above it" | code.claude.com/docs/en/memory, 15:00 KST |
| F10 | F9와 F7의 관계 | 이 세션(`.claude/worktrees/` 아래 데스크톱 worktree)에 실린 프로젝트 지침은 이 worktree의 CLAUDE.md 하나뿐이고, 상위 폴더인 메인 체크아웃의 CLAUDE.md는 실리지 않았다 → 데스크톱 worktree에서는 읽기가 worktree 맨 위에서 멈춘다. 옛 worktree 쪽 직접 증거: dazzling-moore 세션 기록 15·24행에 `Contents of …\dazzling-moore-78f859\AGENTS.md (project instructions, checked into the codebase)`가 실려 있고 CLAUDE.md는 없다 → 옛 worktree에는 옛 AGENTS.md만 실린다 | 이 세션 시작 문맥, dazzling-moore 기록 15·24행 |
| F11 | 옛 규칙과 현재 규칙 차이(예) | 옛 `AGENTS.md:18`(41f7b3f) "update portfolio facts only from explicit user confirmation or a verified read-only broker snapshot" ↔ 현재 `CLAUDE.md:22-23` "Change holdings, cash or cost basis only from a verified read-only broker snapshot" | `git show 41f7b3f:AGENTS.md`, CLAUDE.md |
| F12 | 현재 settings.json | sha256 `459cd04f0dee5aa915fafc0397af2369b9348aab19632505df953d466ea36942`(메인·이 worktree 같음), 59줄, CRLF, 끝 CRLF 1개. `"hooks": {` 43행, `"PreToolUse": [` 44행, `worktree.baseRef` 58행 | `sha256sum`, `od -c`, `grep -n` |
| F13 | 기존 훅 명령 형식 | `python "${CLAUDE_PROJECT_DIR}/.claude/hooks/kiwoom_order_block.py"`, timeout 30, onFailure block | `.claude/settings.json:44-56` |
| F14 | Codex 예약 2개 | `Pre-Open Portfolio Risk Refresh`·`Post-Close Portfolio Strategy` 모두 `status = "PAUSED"`, 둘 다 runtime 경로와 기대 HEAD 41f7b3f 고정. 파일 수정 시각 2026-08-28 | `~/.codex/automations/*/automation.toml` 읽음(15:2x KST) |
| F15 | 이 PC 데스크톱 예약 작업 | 2개(업무 일정 아침 알림·개인 스킬 시험 검토), 저장소·runtime과 무관 | `list_scheduled_tasks` |
| F16 | 앱 설정 | Code 탭 설정에 '기본 기준 브랜치' 항목 없음(worktree 위치만 읽기 전용 표시) | `get_settings` |
| F17 | 작업 순서 보호 | 개발 큐 실행 중 메인 체크아웃의 추적 파일(docs/claude 밖)이 바뀌면 `STOP_MAIN_TOUCHED`(tools/dev_pipeline/README.md:75, devpipe.py:1892-1909). 자동 코어 apply는 지킴 대상 파일의 미커밋 수정이 있으면 멈춤(CLAUDE.md:105-107) | 파일 읽기 |

## 2. 훅 동작 명세

### 2-1. 언제
- `SessionStart`, **matcher 생략**(= 5가지 전부). `fork`도 옛 세션에서 갈라진 새 세션이라 같이 덮는다. 이미 열려 있던 46개 옛 세션은 재개(`resume`) 때 받는다.
- 이미 떠 있는 프로세스는 설정을 시작 때 읽으므로, 병합 뒤 다시 열거나 재개할 때부터 적용된다.

### 2-2. 판정 (파일 상태만 본다)
1. stdin JSON의 `cwd`(문자열)를 읽는다. Windows에서 `/e/사업/…` 꼴(F6)은 `E:/사업/…`로 바꾼다.
2. `cwd`부터 위로 올라가며 `.git`(파일 또는 폴더)이 있는 첫 폴더 = 작업 폴더 맨 위(root). 64단계 안에서 못 찾으면 판정 불가.
3. `root/CLAUDE.md`가 파일로 있으면 → 아무것도 출력하지 않음. 없으면 → 경고.
4. 판정 불가(입력 깨짐, `cwd` 없음·문자열 아님·폴더 아님, root 못 찾음) → 아무것도 출력하지 않음.

왜 이렇게:
- **cwd가 아니라 root를 본다**: 하위 폴더에서 시작하거나 `cd`한 뒤 압축되면 cwd에 CLAUDE.md가 없어도 정상 세션이다(문서: "cwd … moves again when Claude runs cd", F7 쪽 문서 같은 절).
- **`.git`에서 멈춘다**: 모든 `.claude/worktrees/*`의 상위 폴더가 메인 체크아웃이라, 더 올라가면 메인의 CLAUDE.md를 찾아 옛 worktree를 모두 놓친다. 데스크톱 worktree의 CLAUDE.md 읽기도 worktree 맨 위에서 멈춘다(F7·F10).
- **판정 불가면 조용히**: 경고문은 "읽기 전용만"을 말하므로, 정상 Builder·Judge worktree에 거짓 경고가 뜨면 정상 작업을 멈춘다. 이 층은 경고 보조층이고 주 통제는 사장 습관(1단계)이다. 놓친 것은 2주 집계(7절)에서 드러난다. (CLAUDE.md:66 fail-closed와의 관계: 이 훅은 아무 권한도 열지 않으므로 조용함이 허용 범위를 넓히지 않는다. 거짓 경고는 정상 작업에 없는 제한을 더한다.)

### 2-3. 출력
- stdout에 JSON 객체 1개, `ensure_ascii=True`(한국어는 `\uXXXX`로, stdout은 ASCII만):
  `{"systemMessage": <짧은 줄>, "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <경고문>}}`
- 왜 JSON: (1) Windows Python의 파이프 stdout 인코딩(cp949 등)에서 한국어 평문이 깨지거나 예외가 날 수 있는데 ASCII JSON은 그렇지 않다. (2) additionalContext는 화면에 안 보이므로(F8) 사장에게는 `systemMessage`로 한 줄 보인다.
- 길이: additionalContext 1,500자 이하(상한 10,000자의 15%), systemMessage 200자 이하. 테스트로 고정.
- 종료 코드: **모든 경로에서 0**(입력 깨짐·환경변수 없음·한국어/`##` 경로·예외 포함).

### 2-4. 하지 않는 것 (테스트·Judge가 확인)
- git 호출, 네트워크, 파일 쓰기, 파일 열기(`open`) 0. 쓰는 것은 `os.path`의 존재 확인뿐. 환경변수는 `CLAUDE_PROJECT_DIR`만 읽는다(경고문에 메인 CLAUDE.md 경로를 넣을 때만).
- import는 `json`·`os`·`re`·`sys`만. `subprocess`·`socket`·`urllib` 등 0.
- `onFailure` 없음(SessionStart는 원래 막지 못함, F8). settings `timeout` 10초(기본 600초면 멈춘 훅이 첫 답을 오래 붙잡는다 — 문서 "Claude's first response still waits for the hooks to finish"). 한 번 실행 1초 미만.
- 훅 프로세스의 현재 폴더는 메인 체크아웃이다(F7 "Hook commands run in that root") → `os.getcwd()`를 판정에 쓰지 않는다.

### 2-5. settings 변경 (제안 파일로만)
`.claude/settings.json` 43행 `"hooks": {` 바로 다음, 44행 `"PreToolUse": [` 바로 앞에 아래 줄을 **끼워 넣기만** 한다(기존 줄의 바이트 변경 0, CRLF):
```json
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/worktree_base_warn.py\"",
            "timeout": 10
          }
        ]
      }
    ],
```
- 명령 형식은 기존 주문 차단 훅과 같게(F13, REUSE). 데스크톱 worktree 세션에서 `${CLAUDE_PROJECT_DIR}`는 메인 체크아웃을 가리킨다(F6·F7).
- 앞에 끼우는 이유: 뒤에 붙이면 기존 PreToolUse 닫는 줄 `    ]`가 `    ],`로 바뀐다. 앞에 끼우면 기존 줄은 그대로다.

### 2-6. 한계 (정직하게)
- 덮는 범위는 **데스크톱 앱 worktree 세션**이다. 옛 worktree 폴더 안에서 터미널로 `claude`를 바로 켜면 그 폴더의 설정(없음)을 읽어 훅이 아예 없다(문서상 프로젝트 설정은 시작 폴더 기준).
- 경고는 문맥일 뿐 막지 않는다. Claude가 따르지 않을 수 있다 → 7절 2단계 판정.
- 옛 세션이 `.git` 없는 추가 작업 폴더로 `cd`한 뒤 압축되면 조용하다(판정 불가). 반대로 정상 세션이 옛 worktree로 `cd`한 채 압축되면 경고가 뜬다. 셸 `cd`는 작업 폴더 밖이면 시작 폴더로 돌아가므로 드물다.
- 훅은 base 커밋을 모른다(git 호출 없음). "CLAUDE.md 없음 = 2026-09-29 이전 기준"으로 판단하고, 경고문은 "보통 로컬 main 41f7b3f"라고 쓴다(origin/main d574379도 같은 처지, F3).

## 3. 경고문 원문 (고정 — Builder는 이 글자 그대로 넣는다)

`{source}`는 입력의 `source`가 `startup|resume|clear|compact|fork` 중 하나면 그 값, 아니면 `unknown`. `{root}`는 2-2의 root. `{main_claude}`는 `CLAUDE_PROJECT_DIR`가 있고(`/x/…` 꼴이면 2-2처럼 바꾼 뒤) 그 안에 CLAUDE.md가 파일로 있으며 그 폴더가 root와 다를 때 `<CLAUDE_PROJECT_DIR>\CLAUDE.md`, 아니면 `메인 체크아웃(이 worktree가 든 저장소의 맨 위 폴더)의 CLAUDE.md`. `{decided}`는 이 설계의 사장 승인일(KST, `YYYY-MM-DD`) — Builder가 머리 `status`에 적힌 승인일을 글자로 넣는다(자리 표시가 아니라 상수).

additionalContext:
```text
[wt-base-warn v1 · {source}] 투자_V2 작업 폴더 기준 점검 (SessionStart 훅 .claude/hooks/worktree_base_warn.py)
- 사실: 이 세션의 작업 폴더 {root} 맨 위에 CLAUDE.md가 없다. 투자_V2 저장소에는 2026-09-29부터 CLAUDE.md가 있으므로 이 작업 폴더는 그보다 옛 기준(보통 로컬 main 41f7b3f, 2026-08-15)에서 잘렸고, 안의 코드·문서도 그 시점 것이다.
- 사실: 그래서 이 세션에는 옛 AGENTS.md(2026-08)만 실렸다. 옛 규칙은 현재 규칙보다 느슨한 곳이 있다(예: 보유·현금을 바꾸는 근거).
- 현재 규칙 원문: {main_claude}. 읽기만 한다.
- 사장 결정({decided}, docs/claude/wtwarn-1127-design.md 3절): 이런 작업 폴더의 세션은 읽기 전용 검토만 한다. 코드·문서 수정, 커밋·push, 카드 수락, 일지·장부·등록부 기록은 하지 않는다. 현재 규칙을 읽은 뒤에도 같다. 메인 체크아웃이나 다른 폴더의 파일을 절대 경로로 고치는 것도 하지 않는다.
- 수정·커밋·기록이 필요한 일은 사장에게 새 세션을 요청한다: 문서·검토·운영은 Worktree 끔, 코드 분리가 필요하면 기준 브랜치 codex/master-recovery-expansion.
- 이런 세션은 첫 답 첫 줄에서 이 상황을 사장에게 한 줄로 알린다.
```

systemMessage:
```text
[주의] 옛 기준 작업 폴더입니다(맨 위에 CLAUDE.md 없음, 옛 main 41f7b3f 계열). 이 세션은 읽기 전용 검토만 합니다. 고치거나 커밋할 일은 새 세션에서: Worktree 끔, 또는 기준 브랜치 codex/master-recovery-expansion.
```

글 원칙: 사실·결정 문장으로 쓴다(F8 문서 권고). "메인을 절대 경로로 고쳐라", "규칙을 읽었으면 코딩해도 된다", "main으로 커밋·PR·병합하라"로 읽힐 문장이 없다. 사장 결정 문장은 이 설계가 승인되어야 참이 된다 — 승인 전에는 Builder를 시작하지 않고, `{decided}`에는 실제 승인일만 넣는다.

## 4. 대안 검토 (NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)

| 단계 | 안 | 판단 |
|---|---|---|
| NO_CHANGE | 사장 습관(1단계: 검토·문서·운영은 Worktree 끔, 코드 분리는 기준 브랜치 지정)만 | 그대로 유지한다. 다만 이미 열린 46개 옛 세션의 재개와 기본값으로 연 새 세션의 실수는 못 잡는다. 실제로 11/26 policy-a Judge가 옛 worktree `keen-borg-7d091b`(41f7b3f)에서 돌았다(메인 체크아웃 docs/claude/policy-a-merge-2026-11-27.ps1 5-6행). |
| REMOVE | 옛 세션 46개 보관·worktree 정리 | 기존 것은 없어지지만 새 기본값 세션은 계속 생긴다. 옛 대화 재개도 못 한다. 사장이 따로 고를 일(이 설계 범위 밖, 기본 NO_CHANGE). |
| SIMPLIFY | 훅을 줄인다 | 반영: matcher 생략, onFailure 생략, 파일 열기 0, git 0, 판정은 존재 확인 2종뿐. |
| REUSE | 기존 틀 | 반영: 명령 형식(F13), 제안 settings 파일 + 사장 병합 스크립트 틀(9c32545 kiwoom-block, policy-a-merge-2026-11-27.ps1), 테스트의 고정 기준 settings 방식(test_kiwoom_order_block_hook.py 25-27행). |
| REPLACE | main 옮기기 | 제외: runtime worktree가 main을 체크아웃, Codex 예약 2개가 41f7b3f 고정(F14), 사장 계획. |
| REPLACE | 앱 기본 기준 브랜치 바꾸기 | 불가: Code 탭 설정에 항목 없음(F16). `worktree.baseRef: "head"`는 이미 있으나(F12) 데스크톱 앱이 옛 main에서 잘랐다(부모 세션 관찰; 문서에 앱이 이 값을 따른다는 문장 없음). |
| ADD | 이 경고 훅 | 채택. |
| ADD | 2단계 차단 가드(PreToolUse) | 이번 범위 밖. 7절에서 2주 뒤 판단, 기본 NO_CHANGE. |

## 5. 연결표 (CLAUDE.md:132 · analysis-linkage-map-2026-10-05.md 1절 8항)

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 경고 문맥(additionalContext, `[wt-base-warn v1 · …]`) | `.claude/hooks/worktree_base_warn.py`, settings `hooks.SessionStart`, 세션 시작·재개·clear·압축·분기 때마다. **끊김 — 아직 없음.** 메울 변경: wtwarn-1127-builder-prompt.md · 승인 경로: 이 설계 사장 승인 → Judge A PASS → 사장 PowerShell 병합 | 옛 기준 worktree의 Claude 세션. Claude Code가 첫 요청 전에 문맥에 넣는다(hooks 문서 'Add context for Claude': "SessionStart and SubagentStart: at the start of the conversation, before the first prompt") | 그 세션이 수정·커밋·기록을 하지 않고 첫 답 첫 줄에서 사장에게 새 세션을 요청(세션 안내만. 매매 규칙·알림·주문표 경로 없음) | 훅 안의 오류는 일부러 조용히 끝난다(종료 0, stderr 0). python을 못 찾거나 시간 초과일 때만 SessionStart가 stderr를 사장 화면에 보인다(hooks 문서 종료 코드 표 "Shows stderr to user only"). 조용한 놓침은 병합 뒤 점검(Judge 지시문 B절)과 7절 '놓침 수' 집계로 안다 | 끊김(승인 뒤 병합으로 메움) |
| 사장 화면 한 줄(systemMessage) | 같음 | 사장. hooks 문서 systemMessage "Warning message shown to the user". 데스크톱 앱 표시 여부는 **확인 필요** → Judge B절 La | 사장이 Worktree 끔 / 기준 브랜치 지정으로 새 세션을 연다. 사람 단계: 세션을 여는 것은 원래 사장 일이고, 이 줄은 단계를 늘리지 않고 잘못된 설정만 알린다(헌법 §3 결함 아님) | 안 보이면 La에서 안다. 그때도 문맥 쪽 '첫 답 첫 줄 알림'이 남는다 | 끊김(같음) |
| 발동 기록(세션 기록 속 표지 `[wt-base-warn v1`) | 훅은 파일을 쓰지 않는다. Claude Code가 주입 문맥을 세션 기록에 저장(hooks 문서 "Claude Code saves the injected text in the session transcript") | 병합 + 14일 판정 세션(7절 집계 방법). 깨우는 곳: 관제판 작업 `wtwarn-p2`를 `status: waiting`, `resume: {type: date, date: 병합 + 14일}`로 둔다 — 그날 '재개 가능'이 되어 다음 관제판 갱신 세션이 집계를 한다(dev-dashboard-protocol.md:45-47). 집계가 기준을 넘을 때만 결정 작업(ask·default NO_CHANGE·deadline·answerHint `결정 wtwarn-p2: `, 같은 문서 36-41행)으로 바꿔 사장에게 묻고, 0건이면 NO_CHANGE를 기록하고 done(CLAUDE.md:138 — 변경을 제안할 때만 묻는다). 찾아보는 색인: `active-decisions.md`의 `wtwarn-p2` 1줄. **끊김 — 둘 다 아직 없음.** 메울 변경: 9절 2·7(관제판을 갱신할 수 있는 세션이 만든다) | 2단계 가드를 제안할지(기본 NO_CHANGE) | 집계 세션이 안 돌면 관제판에 '재개 가능'으로 계속 보인다. 기준을 넘긴 뒤 답이 없으면 deadline에 NO_CHANGE로 닫히고 알림만(6절) | 끊김(승인 뒤 메움) |

## 6. 기본 처분 (사전 등록)
- **이 설계**: 2026-12-04 KST까지 사장 답이 없으면 NO_CHANGE(훅 안 만듦, 1단계 습관만), 알림만.
- **Judge A**: FAIL 또는 PASS_WITH_FIX면 병합하지 않는다(NO_CHANGE). 고친 판으로 Judge A를 다시 받는다.
- **병합 뒤 점검(Judge B)**: 정상 세션(Worktree 끔·`claude --worktree`·`claude -p`)에 경고가 뜨면(거짓 양성) 사장이 되돌리기 한 줄을 바로 실행한다(병합 스크립트가 그 줄을 출력). 옛 세션에 경고가 안 뜨면(거짓 음성) 되돌리지 않고(해가 없음) 고칠 Builder를 따로 돌린다.
- **2단계 가드**: 7절 기준 미충족이거나 판정일에 답이 없으면 NO_CHANGE.
- 어떤 기본값도 노출·예산·권한을 올리지 않는다.

## 7. 2단계 가드 판정 (병합 + 14일, 기본 NO_CHANGE)
- 판정일: 병합 커밋 날짜 + 14일(Judge B 보고서가 날짜를 적는다).
- 집계(읽기 전용, 판정 세션이 직접): `~/.claude/projects/*/*.jsonl` 가운데 `[wt-base-warn v1` 을 담은 기록 = 발동 세션. 세션마다 표지 줄 뒤에 (가) `Edit`·`Write`·`NotebookEdit` 도구 호출, (나) 명령에 `git commit`·`git push`가 든 Bash·PowerShell 호출이 있었는지 센다. source별 발동 수도 적는다. 놓침 수도 센다: 병합 뒤 시작·재개된 기록 가운데 `cwd`가 맨 위에 CLAUDE.md 없는 worktree인데 표지가 없는 세션 수(1건 이상이면 훅 결함 → 고칠 Builder, 2단계와 별개). Judge B의 시험 세션은 빼고 센다(Judge B 보고서의 세션 id 목록).
- 기준(미리 고정): 14일 안에 (가) 또는 (나)가 **1건 이상** 있으면 2단계 가드 설계를 사장에게 제안한다. 0건이면 NO_CHANGE로 닫고 알림만.
- 2단계 가드를 만들게 되면 그것도 .claude/** 수동 경로이며 별도 승인이다.

## 8. 바뀔 조건 (V4)
- 병합 뒤 La에서 경고가 안 뜨고 원인이 `${CLAUDE_PROJECT_DIR}`가 메인이 아닌 경우 → 명령 형식을 다시 설계(F6·F7이 틀린 경우).
- Claude Code가 중첩 worktree에서 상위 CLAUDE.md까지 읽기 시작하면(F10 변화) → 경고문 '옛 AGENTS.md만 실렸다' 문장을 고친다.
- 앱에 기본 기준 브랜치 설정이 생기면(F16 변화) → 그 설정으로 바꾸고 훅은 남길지 다시 본다.
- 14일 집계 (가)·(나) ≥ 1 → 2단계 가드 제안.
- systemMessage가 앱에 안 보이면 → 문맥 쪽 첫 줄 알림만으로 충분한지 사장 확인.

## 9. 승인 뒤 순서 (이 세션은 여기서 멈춤)
1. 사장 승인(이 세션 대화). 승인 문구·시각을 이 문서 머리 `status`에 적는다.
2. 메인 체크아웃에 쓸 수 있고 관제판을 갱신할 수 있는 세션(Cowork 또는 사장실 회사PC 스레드, Worktree 끔)이 같은 날, 1의 `status` 기록이 끝난 뒤: (가) 이 문서·Builder·Judge 지시문 3개를 설계 worktree에서 메인 `docs/claude/`로 **같은 바이트로** 옮기고(sha256 대조) `_pending`에 올린다 — 이후 Builder·Judge·병합 스크립트는 메인 사본을 원본으로 쓴다. (나) `active-decisions.md`에 `wtwarn-1127`(1단계 습관 + 이 훅)·`wtwarn-p2`(판정일 = 병합 + 14일, 기본 NO_CHANGE) 2줄을 덧붙이고(sha256 확인 뒤 덧붙이기만), 관제판에 `wtwarn-1127` 작업을 올린다(dev-dashboard-protocol.md). 이 설계 세션은 메인 쓰기가 막혀 있어 하지 못한다.
3. 동시 개발 상한(CLAUDE.md:140, 개발 3건·권한 1건) 확인.
4. Builder: 메인 체크아웃 폴더에서 `claude --worktree wtwarn-1127`(Opus 5.5, effort high)로 열고 메인 `docs/claude/wtwarn-1127-builder-prompt.md`(2에서 옮긴 사본)를 따르게 한다. 시작 주체: 사장 터미널, 또는 사장 승인 뒤 Cowork(Desktop Commander, CLAUDE.md:150-152)·사장실 회사PC 스레드(CLAUDE.md:98-99).
5. Judge A(병합 전): 데스크톱 새 세션 **Worktree 끔**(메인 체크아웃, 읽기 전용), Opus 5.5 effort xhigh, 메인 `docs/claude/wtwarn-1127-judge-prompt.md` A절. Worktree를 켜면 옛 기준에 떨어질 수 있다 — 이 설계가 고치려는 바로 그 문제.
6. 사장 병합: 사장 PowerShell 한 줄(Builder가 만들고 Judge A가 검토한 `wtwarn-1127-merge.ps1`).
7. Judge B(병합 뒤 실제 세션 점검) → 판정일 기록. 관제판 갱신 세션이 `wtwarn-p2` 작업을 `status: waiting`, `resume: {type: date, date: 병합 + 14일}`로 올린다(5절 표 3행). 그날 집계해 기준(7절)을 넘으면 결정 작업(`ask` = "옛 기준 worktree에서 수정·커밋을 막는 2단계 가드를 만들까요?", `default` = NO_CHANGE, `deadline`, `answerHint` = `결정 wtwarn-p2: `)으로 바꾸고, 0건이면 NO_CHANGE 기록 뒤 done.

## 10. 열린 확인 (부모 세션이 넘긴 3건)
| 확인 | 결과 | 근거 |
|---|---|---|
| 41f7b3f에 고정된 Codex 예약 2개가 아직 PAUSED인가 | **예, 둘 다 PAUSED** (2026-11-27 읽음). Codex는 Claude 훅을 읽지 않으므로 이 설계와 무관 | F14 |
| SessionStart가 headless `-p` Builder·Judge에서도 도는가 | **확인 필요**(문서에 직접 문장 없음. `initialUserMessage`가 "-p" 모드용이라는 문장은 돈다는 쪽 정황). 결론 영향 없음: Builder·Judge·개발 큐 worktree는 모두 CLAUDE.md가 있어 돌아도 출력 0 | F8, Judge B Ld에서 기록으로 확인 |
| SessionStart 출력 형식·matcher·상한 재확인 | **확인함**: matcher 5종, additionalContext/평문 stdout, systemMessage, 10,000자 상한, 막지 못함, 사실 문장 권고 | F7·F8 (hooks·worktrees 문서 원문, 2026-11-27) |

## 11. 검토 기록
- 내장 재검토 1회(Fable 5.2, effort high, 3-1 지시문, 2026-11-27): 8건 — 결론 바뀜 1(병합 뒤 기존 주문 차단 테스트 `test_live_settings_are_the_base_or_exactly_the_proposed_file`이 반드시 실패 → 허용 파일에 그 테스트 1곳 추가, Judge A가 병합 뒤 상태로도 돌림) · 정정 7(병합 스크립트 틀을 policy-a로·커밋 전 되돌리기·시간대 05:45/23:05, Judge 보고서 해시 목록을 신뢰 기준으로·순환 제거, 경고문 끝 문장·승인일 자리·'main 병합 권유' 확인, 연결표 ⑤ 문구·놓침 수 집계·관제판 기한으로 깨우기, `--no-optional-locks`·`$PSScriptRoot` 상대 경로, 시간 시험 느슨하게·`CLAUDE_PROJECT_DIR` 경로 변환·Judge B 보강, 행 인용 3건). 8건 모두 이 세션에서 원문을 다시 열어 맞음을 확인하고 반영(test_kiwoom_order_block_hook.py:344-349, policy-a-merge-2026-11-27.ps1:49-109·184-237, dev-dashboard-protocol.md:36-41, CLAUDE.md:98-99·150-154, dazzling-moore 기록 15·24행). 미반영 0. (작업자 236k 토큰, 9.6분)
- 2회차(Fable 5.2, high, 고친 부분만): 6건 — 결론 바뀜 0 · 정정 6(Restore-Main이 인덱스까지 되돌리고 남으면 `ROLLBACK_INCOMPLETE`, Judge 해시 절 제목을 ASCII `## merge-sha256`·줄 형식 고정, 설계 문서 3개는 승인 뒤 메인 사본이 원본·병합 스크립트는 확인만, 두 번째 `Test-Windows` 뒤 새 경로 부재·보관 바이트 재확인, kiwoom 테스트 블록은 함수 안 지역 bytes, `wtwarn-p2`는 waiting + 날짜 재개로 두고 기준을 넘을 때만 결정 작업). 6건 모두 원문 재확인 뒤 반영(policy-a-merge-2026-11-27.ps1:176-197·225-236, dev-dashboard-protocol.md:45-47, CLAUDE.md:138). 미반영 0. 최대 2회 규칙에 따라 재검토 끝. (작업자 179k 토큰, 6.5분)

검토 완결: 원문 확인 17/17(1절 F1~F17, 이 세션에서 직접 열거나 실행) · 내장 재검토 2회(반영 14건, 결론 바뀜 1) · 미해결 2(데스크톱 앱의 systemMessage 표시, SessionStart의 `-p` 발동 — 둘 다 Judge B에서 확인, 지금 결론 영향 없음) · 자료 시점 2026-11-27 14:47~16:30 KST · 바뀔 조건 8절
