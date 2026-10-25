---
id: claude-settings-audit-2026-10-25
type: audit
status: current (읽기 전용 조사, 아무것도 고치지 않음)
as_of: 2026-10-25
summary: "회사PC 저장소의 Claude Code 설정·훅·권한 규칙에 주문·apply 차단이 있는지 읽은 결과와, 사장이 넣을지 판단할 보강 후보."
source_decision: "Projects 진단 결정 2 '조사 먼저' (사장 '권장안대로', 사장실 스레드 직접 입력, 2026-10-25 10:30Z)"
consumers: "사장 · 사장실 코디네이터 · (넣게 되면) K3 Builder/Judge"
authority: "order_authority=false · quantity_authority=none · 설정 수정 없음 · 비밀 파일 읽지 않음"
---

# 결론
- **저장소 `.claude/settings.json`에 기계 차단(deny)이 있다.** 주문 도구 1개, `auto_core.py`, 대조·일지 `apply`, 상태·원장·일지 직접 편집, `dev-run/dev-merge/dev-queue`, `.claude` 설정 편집, 루트 `.env*` 읽기가 막혀 있다.
- **훅(hooks)은 없다.** 읽기 전용 허용(allow) 규칙도 없다(`settings.local.json`에 `Bash(cd *)` 하나뿐).
- **구멍 후보 3개**: ① 키움 주문 차단이 도구 이름 1개(`kiwoom_order_submit`)뿐인데 이 세션 목록에는 그 이름이 없다. ② 이 저장소 규칙이 **이 사장실 스레드의 도구에 적용되는지 확인 필요**(이 스레드는 PC의 Claude Code가 아니라 원격 도구 `mcp__remote-devices__*`로 파일을 읽고 쓴다). ③ 비밀 읽기 차단이 `./.env`, `./.env.*` 두 줄뿐.
- 넣는 일은 `.claude` 수정이라 Claude 세션 금지 → **사장 본인 또는 K3**. 이 문서는 후보만 적는다.

# 1. 읽은 것 (원문 위치)
| 파일 | 내용 |
|---|---|
| `.claude/settings.json` (전체 읽음) | `permissions.ask` 8줄, `permissions.deny` 22줄, `worktree.baseRef=head`, `effortLevel=medium`. `hooks` 키 없음 |
| `.claude/settings.local.json` (전체 읽음) | `permissions.allow = ["Bash(cd *)"]` 한 줄. 비밀 값 없음 |
| `.claude/agents/summarizer.md`, `test-runner.md` | 도구 제한(summarizer = Read·Glob·Grep, test-runner = Bash·Read·Grep·Glob), 모델 haiku. 둘 다 본문에 apply·키움·`.env` 금지 문구 |
| `.git/hooks/` | 샘플 파일만(실제 훅 없음) |
| `.githooks/pre-push` | 파일 존재만 확인. **내용은 읽지 않음**(이 조사 범위 밖, `core.hooksPath` 연결 여부는 확인 필요) |
| 저장소 루트 `.mcp.json` | 검색 결과 없음 |
| 읽지 않은 것 | `.env.local`(루트에 있음, 비밀), `~/.claude/` 전역 설정, 관리형(managed) 설정 — 이 스레드 허용 폴더(`E:\...`) 밖이거나 비밀이라 읽지 않았다 → 전역 설정 상태는 **확인 필요** |

# 2. 차단 현황표 (settings.json deny/ask)
| 막으려는 것 | 규칙 | 평가 |
|---|---|---|
| 주문 도구 | `mcp__*__kiwoom_order_submit` | **약함.** 이 세션 키움 도구 이름은 `kiwoom_commands`·`kiwoom_help`·`kiwoom_query`뿐이라 이 규칙에 걸리는 도구가 보이지 않는다. 주문이 `kiwoom_commands`/`kiwoom_query` 안의 명령·인자로 가능한지는 **확인 필요**(지침 1절: 확인 전 `kiwoom_commands` 호출 금지) |
| 대조·일지 apply | `*reconcile_broker_state.py apply*`, `*reconcile_broker_state.py auto*`, `*portfolio_review_journal.py apply*` (Bash·PowerShell 각각) | 문자열 포함 검사. `python -c`로 모듈을 불러 호출하는 방식 등 우회는 이 규칙으로 못 막음(CLAUDE.md는 절차로 금지) |
| auto-core | `*auto_core.py*` | 읽기 명령(`cat auto_core.py` 등)도 같이 막힘(CLAUDE.md 91행 설명대로) |
| 개발 파이프라인 | `*dev-run.ps1*`, `*dev-merge.ps1*`, `*dev-queue.ps1*` | `register-dev-tasks.ps1`, `commit-docs.ps1`, `run-docs-commit.ps1`, `tools/dev_pipeline/devpipe.py` 직접 호출은 deny에 없음 |
| 설정 편집 | `Edit(/.claude/settings.json)`, `Edit(/.claude/settings.local.json)` | `Edit` 도구만. 다른 쓰기 도구(원격 파일 도구 등)에 적용되는지는 확인 필요 |
| 상태·원장·일지 | `Edit(/stock-strategy-system/portfolio_state.json)`, `reconciliation_ledger.jsonl`, `backups/**`, `decision_journal.json` | 같은 한계 |
| 비밀 | `Read(./.env)`, `Read(./.env.*)` | 루트 `.env.local`은 `.env.*`에 걸림. 그러나 하위 폴더의 `.env*`, 토큰 파일, `workspace/private_inputs/**`는 규칙이 없고, `Read` 규칙은 셸 `cat`을 막지 못한다는 점은 **공식 문서 재확인 필요** |
| 물어보고 하기(ask) | `Edit(/tools/**)`, `Edit(/CLAUDE.md)`, `Edit(/AGENTS.md)`, `Edit(/.gitignore)`, `Edit(stock-strategy-system/**)`, `Edit(workspace/policies/**)`, `git commit`, `git push` | 금지가 아니라 확인 요청. CLAUDE.md 98행 "커밋·푸시는 요청 때만"과 같은 방향 |

# 3. 이 사장실 스레드에 적용되는가 (가장 중요한 확인 필요)
- 이 스레드가 쓰는 파일·셸 도구는 `mcp__remote-devices__Filesystem__*`, `device_bash`(Linux VM), Desktop Commander 등 **원격 연결 도구**다. 위 deny 규칙은 `Bash(...)`, `PowerShell(...)`, `Edit(...)`, `Read(...)` 도구 이름 기준이라, **이 도구들에도 걸리는지 이 읽기 조사로는 증명하지 못했다.** 공식 문서(진단 문서 2절 3항)는 "로컬 스레드는 PC의 설정·훅·권한 규칙을 적용받는다"고 하지만 이 세션의 도구 이름 구성과 맞는지는 시험해야 안다.
- 시험은 하지 않았다(차단 시험은 금지 동작을 시도하는 일이라 이 조사에 넣지 않음). 시험하려면 K3로 "무해한 대상" 시험 항목을 먼저 설계해야 한다.
- 따라서 지금 이 스레드를 막는 확실한 장치는 **프로젝트 지침 1·3·4절(문장)**이다. 파일 도구로 `.claude/settings.json`을 쓸 수 있는 도구가 목록에 있다는 점은 사실이며(`Filesystem__write_file` 등), 쓰지 않는 것은 지침과 이 세션의 규율에 달려 있다.

# 4. 보강 후보 (사장 판단용 — 하나도 적용하지 않음)
각 항목은 **강화만** 한다(허용 범위를 넓히지 않음). 넣는 방법은 사장 본인 또는 K3 Builder/Judge.
1. **키움 도구 이름 전체 차단 검토**: `mcp__*__kiwoom_commands`를 deny에 추가하거나, 주문 가능 여부 확인(읽기 조회 `kiwoom_help`로 사장이 직접 요청) 뒤 결정. 루틴 조회는 `kiwoom_query`만 쓰므로 영향이 작을 것으로 보이나 영향 범위는 확인 필요.
2. **인자 기준 차단은 규칙이 아니라 PreToolUse 훅**: 주문 API 표지(`/api/us/ordr`, `ust2000`, `ust2001`)가 요청에 들어 있으면 거절하는 훅. MCP 도구 호출에도 훅이 걸리는지 공식 문서에서 확인 필요.
3. **비밀 읽기 규칙 확대**: `Read(**/.env*)`, `Read(workspace/private_inputs/**)` 등. 셸 `cat` 우회는 훅이 필요할 수 있음.
4. **deny 보강 후보**: `register-dev-tasks.ps1`, `commit-docs.ps1`, `devpipe.py` 직접 호출. (`commit-docs.ps1`은 예약 작업이 쓰므로 Claude 세션에서만 막는지 확인 필요)
5. **읽기 전용 허용 규칙(진단 아이디어 C)**: `git status/log/diff/show`, `grep`, `cat` 허용. 막힘 감소용이며, 로컬 스레드 auto mode와 허용 규칙의 결합 방식은 **확인 필요**(permission-modes 문서 미열람). 안전 강화는 아니므로 1~4보다 뒤.
6. **`.githooks/pre-push` 내용 점검**(읽기): 지금 push 방어가 실제로 켜져 있는지.

# 5. 이 조사가 하지 않은 것
설정 수정, 훅 설치, 차단 시험, `.env.local`·전역 설정·토큰 읽기, 키움 도구 호출, 승인류 실행.

검토 완결: 원문 확인 settings.json 전체 · settings.local.json 전체 · agents 2개 전체 · .git/hooks 목록 · .githooks 목록 · CLAUDE.md 91·98행 · 내장 재검토 없음(권한 변경을 제안하지 않는 조사) · 미해결 확인 필요 7(전역 설정, 이 스레드 도구 적용 여부, kiwoom_commands 주문 가능 여부, Read 규칙과 셸, MCP 훅, pre-push 내용, 허용 규칙 결합) · 자료 시점 2026-10-25 · 바뀔 조건: `settings.json`이 바뀌거나 이 스레드의 도구 구성이 바뀌면 3절부터 다시 본다.
