# 개발 파이프라인 (재설계 T3) — Cowork 작성법

일반 변경 한 건 = Cowork가 지시문 + 큐 파일을 쓰고, READY_TO_MERGE면 Cowork가 PC에서 `.\tools\dev-merge.ps1 <id>`를 실행한다(사장 결정 dc-dev Q1 a, 2026-10-22 — docs/claude/dc-dev-2026-10-22.md).
권한·한도 변경과 파이프라인 자체(보호 경로) 변경은 이 파이프라인을 쓰지 않는다(기존 방식: worktree Builder + 별도 Judge + 사용자).

## 흐름

1. Cowork: `docs/claude/<id>-builder-prompt.md`(아래 dev-run 블록 포함) + `docs/claude/_pending/<id>.txt`(지시문 커밋 목록) + 큐 파일 `docs/claude/_dev-queue/<id>.txt`.
2. Windows 작업 `InvestmentV2-DevQueue`(5분마다) → `tools/dev-queue.ps1`: 잠금 확인 → 가장 오래된 큐 1개를 `workspace/outputs/dev-runs/_taken/`으로 옮김 → 지시문이 커밋돼 있지 않으면 `commit-docs.ps1` 1번 → `tools/dev-run.ps1 <id>`.
3. dev-run: preflight(경로 길이 포함) → 기준선 임시 worktree 준비(같은 base SHA·python·방식이면 캐시) → 헤드리스 Builder(`claude -p --worktree <id>`)와 기준선 전체 스위트를 **동시에** → Builder 끝 → 기준선 끝을 기다림 → 메인 체크아웃 비교 → 스크립트 판정(범위·보호 경로·위생·테스트·스키마) → 헤드리스 Judge(Read·Grep·Glob만) → 실패면 같은 worktree에서 수정 1회 → 결과.
4. Cowork: `.\tools\dev-merge.ps1 <id>`. authority면 이 대화에 사장 결정 문구가 있을 때만, 사장이 직접 연 PowerShell 창에서 `-ApproveAuthority`로 실행하고 id를 한 번 더 입력한다(hnd-check: 입력·출력이 리다이렉트됐거나 ConsoleHost가 아니면 `STOP_NOT_INTERACTIVE`, id가 다르면 `STOP_ID_NOT_CONFIRMED`. Cowork는 `-ApproveAuthority`를 붙이지 않는다).
5. Windows 작업 `InvestmentV2-DocsCommit`(매일 23:30): `tools/run-docs-commit.ps1` → `commit-docs.ps1` (결과 요약 `docs/claude/dev-runs/<id>.md`도 이때 커밋된다).

## 지시문 (`docs/claude/<id>-builder-prompt.md`)

- `<id>`: `^[a-z0-9][a-z0-9-]{1,47}$`. 한 번만 쓴다(같은 id의 run 폴더·worktree·브랜치가 있으면 preflight에서 멈춤).
- id는 **14자 이하 권장**(지금 저장소·경로 기준). preflight가 정확히 검사한다: `.claude/worktrees/<id>`와 기준선 임시 이름 `_base-<sha8>` 아래 최장 추적 파일 경로가 259, 폴더 경로가 247(UTF-16 단위)을 넘으면 `STOP_PREFLIGHT reason=PATH_TOO_LONG:<필요>>259:max_id=<허용 최대 id 길이>`.
- 본문: 목표, 바꿀 내용, 테스트, 보고 위치, 그리고 `## Judge 확인 항목`(Judge가 G8로 하나씩 본다).
- 지시문 안에 ```` ```dev-run ```` 펜스 **정확히 1개**, 안은 JSON 한 개, **ASCII만**:

```dev-run-example
{"task_id": "fix-card-footer", "class": "general", "builder_model": "sonnet", "builder_effort": "high",
 "max_turns": 80, "builder_timeout_min": 45,
 "allowed_paths": ["manage-us-stock-strategy/scripts/render_card.py",
                   "manage-us-stock-strategy/tests/test_render_card.py",
                   "docs/claude/fix-card-footer-report.md"],
 "target_tests": ["test_render_card*.py"],
 "commit_message": "fix(card): footer shows snapshot time"}
```

(실제 지시문에서는 펜스 이름을 `dev-run`으로 쓴다. 이 README는 예시라서 다른 이름을 쓴다.)

| 키 | 값 |
|---|---|
| task_id | 파일 이름의 id와 같아야 함 |
| class | `general` 또는 `authority` (authority는 builder_model `opus`만) |
| builder_model / builder_effort | `opus`·`sonnet` / `low`·`medium`·`high`·`xhigh` |
| max_turns / builder_timeout_min | 1~300 / 1~120 (수정 1회차는 각각 절반, 올림) |
| allowed_paths | 정확한 파일 경로 또는 `디렉터리/`. `*`, `..`, 절대 경로, 백슬래시 금지. 보호 경로와 겹치면 거절 |
| target_tests | `test_x*.py` 같은 discover 패턴(비어 있으면 거절) |
| commit_message | ASCII 한 줄(200자 이하). dev-merge가 `Dev-Run: <id> base=… judge=…` 꼬리를 붙인다 |

- 알 수 없는 키·빠진 키는 거절. 보고 파일(예: `docs/claude/<id>-report.md`)도 allowed_paths에 **정확한 파일 경로**로 넣는다(`docs/claude/` 같은 디렉터리는 지시문 자신을 덮어서 거절된다). 테스트 파일도 정확한 경로로 쓴다(`manage-us-stock-strategy/tests/` 디렉터리는 파이프라인 자체 테스트를 덮어서 거절된다).
- **authority 작업은 사용자 결정 기록이 있을 때만 큐에 넣는다.** 그래도 병합은 `-ApproveAuthority` 1번이 더 필요하다. 수동 경로 권한 병합 스크립트(`docs/claude/<id>-merge-*.ps1`)도 같은 검사(`[Console]::IsInputRedirected`·`[Console]::IsOutputRedirected`·`$Host.Name -eq 'ConsoleHost'` + id 재입력)를 넣는다.

## 큐 파일 (`docs/claude/_dev-queue/<id>.txt`, git 무시)

첫 줄 = `<id>` (파일 이름과 같아야 함). 나머지 줄은 메모(읽지 않음). 형식이 틀리면 `_taken/`으로 옮기고 `LATEST.json`에 `STOP_QUEUE_INVALID`.

## 보호 경로 (P6 — devpipe.py 상수, 지시문으로 못 바꿈)

`tools/**` · `.claude/**`(어느 깊이든 `.claude` 폴더, 기준 커밋에 없는 무시 파일 포함) · 어느 깊이든 `CLAUDE.md`·`CLAUDE.local.md`·`AGENTS.md`·`.mcp.json`·`.gitignore`·`.gitattributes`·`.worktreeinclude` · `manage-us-stock-strategy/tests/test_dev_pipeline*.py` · `docs/claude/dev-runs/**` · `docs/claude/_pending/**` · `docs/claude/_dev-queue/**` · 그 작업의 지시문 · `workspace/policies/**` · `stock-strategy-system/**`.
Builder가 이것을 만들거나 고치면 테스트·Judge·재시도 없이 `STOP_PROTECTED`. 예외: Claude Code가 새 worktree에 복사하는 무시 파일(`.worktreeinclude` 목록, `.claude/settings.local.json`)이 Builder 1회차 시작 바로 앞에서 잰 메인 사본과 sha256이 같을 때, 그리고 `__pycache__/*.pyc`.

## 권한 경로 (P7 — `authority-paths.txt`)

여기 있는 경로를 바꾸거나, 추가된 줄에 주문 표지(`/api/us/ordr`, `ust2000`, `ust2001`, `kiwoom_order`, `order_submit`, `overseas orders`, `order_authority … true`)가 있거나, 추가된 줄에 `kill_switch`가 있거나, 추가된 줄에서 `:`·`=` 바로 뒤 값(스키마 `{"const": X}`·`{"type": X}`는 X)이 `watchlist_approved`·`active_universe_approved`·`new_buy_instrument_approved` = true, `quantity_authority` ≠ none/null/false, `execution_quantity` ≠ null/None이거나, 지운(또는 바꾼) 줄에 `order_authority`·`kill_switch`·`quantity_authority`·`execution_quantity`·`watchlist_approved`·`active_universe_approved`·`new_buy_instrument_approved`가 있거나, Judge가 `class_ok=false`를 쓰면 class = authority(내려가지 않음) → `NEEDS_APPROVAL`.

`ORDER_TICKET_HUMAN_ENTRY`(주문 1단계 표지)는 `quantity_authority` 값이 none이 아니므로 새 줄에 쓰이면 authority다 — 의도된 동작이며, 주문표 모듈은 이미 권한 경로다.

## 결과 읽기

- 한 줄 요약: `workspace/outputs/dev-runs/LATEST.json` (`line`, `status`, `next`).
- 정본: `workspace/outputs/dev-runs/<id>/` — `result.json`, `run.json`, `log.txt`, `checks-N.json`, `attempt-N/`(diff.patch, 테스트 출력), `judge-N.json`(봉투 원본), `judge-N/`(Judge에 준 자료), `builder-N.json`.
- 사람용 요약: `docs/claude/dev-runs/<id>.md` (Judge 보고 원문 포함, 23:30 자동 커밋).

| status | 뜻 | 다음 |
|---|---|---|
| READY_TO_MERGE | 테스트·Judge PASS, general | Cowork가 `.\tools\dev-merge.ps1 <id>` 실행 후 알림 |
| NEEDS_APPROVAL | PASS지만 authority | 이 대화의 사장 결정 → 사장이 대화형 PowerShell 창에서 `.\tools\dev-merge.ps1 <id> -ApproveAuthority` + id 재입력 |
| FAIL | 수정 1회 뒤에도 테스트 실패 또는 Judge FAIL | Cowork가 새 id로 다시 쓰거나 중단 |
| BLOCKED | Builder가 BLOCKED.md를 씀(판단 필요) | Cowork가 이유를 보고 결정 |
| JUDGE_ERROR / TIMEOUT | Judge 출력을 못 읽음 / 시간 초과 | 재시도 없음. 새 id로 |
| STOP_PROTECTED / STOP_SCOPE / STOP_SECRET | 보호·허용 경로 밖·비밀 파일 이름 | 재시도 없음 |
| STOP_MAIN_TOUCHED / STOP_RUN_RECORD_CHANGED | 실행 중 메인 체크아웃(정책·상태·추적 파일)이 바뀜 / run 기록(run.json·기준선·표지 파일)이 바뀜 | 재시도 없음. 원인 확인 뒤 새 id |
| STOP_PREFLIGHT 등 STOP_* | 시작 조건 실패(reason 참고) | 원인 해결 뒤 새 id |

## 고정 상수 (지시문·머리말로 못 바꿈)

- Builder: `--permission-mode acceptEdits --permission-prompts none --strict-mcp-config --setting-sources project --tools "Read,Edit,Write,Grep,Glob,Bash,PowerShell"` + `--disallowedTools "mcp__*" "Bash(git *--output*)" "PowerShell(git *--output*)" "Bash(git *--no-index*)" "PowerShell(git *--no-index*)"` + `--allowedTools`(`python -m unittest …`, 스키마 감사, `git status|diff|log`만 — 이름만 있는 Read·Edit·Write·Grep·Glob 규칙은 넣지 않는다: worktree 밖 경로까지 승인하기 때문). worktree 안 읽기는 원래 승인이 필요 없고 편집은 acceptEdits가 승인한다. 그 밖에 묻는 것은 모두 거절된다.
- 복사 파일 스냅샷: Builder 1회차 시작 바로 앞에서 다시 잰다(`devpipe.py snapshot-includes`, run.json `include_snapshot`; init-run 값은 `include_snapshot_init`). 수정 회차는 같은 스냅샷을 쓴다.
- dev-queue 상한: commit-docs 15분 + dev-run 340분 + 여유 5분 = 작업 한도 360분.
- Judge: `--model opus --effort xhigh --tools "Read,Grep,Glob"`, 같은 MCP·설정 제한, 80턴, 45분.
- 테스트: `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1`, 실행마다 새 `PYTHONPYCACHEPREFIX`. 새 실패 = 실패 id − 기준선. Ran 감소·skipped 증가·`expected failures` 증가·`def test_` 감소·테스트 파일 삭제·스키마 감사 FAIL = 실패(재시도 대상). Ran 줄이 없으면 `STOP_TESTS_DID_NOT_RUN`.
- 기준선: 임시 worktree `.claude/worktrees/_base-<sha8>`을 브랜치 `devpipe-base-<sha8>` 위에 만든다(Builder worktree와 같은 브랜치 조건). 캐시 키 `<base>-py<버전>-b2.json`(detached 시절 캐시는 쓰지 않음). Builder와 동시에 돌고(로그 `BASELINE start/end`), 상한은 그대로(전체 60분 + 스키마 10분, 바깥 75분). 어느 종료 경로든 잠금 해제 전에 그 worktree와 **이 실행이 만든** `devpipe-base-` 브랜치(base를 가리킬 때만)를 지운다. check는 base·python·방식이 같은 `baseline.json`만 쓴다(없으면 `STOP_BASELINE_MISSING`).
- 기록·메인 보호(O3): run.json·baseline.json·기준선 캐시·표지 파일의 sha256을 dev-run 프로세스가 단계마다 기억하고 다음 단계 전에 대조(`STOP_RUN_RECORD_CHANGED`). Builder 1회차 직전에 메인의 추적 파일 상태 줄(docs/claude/ 밖)과 `workspace/policies/`·`stock-strategy-system/` 전 파일 sha256을 찍고 check 직전마다 비교(`STOP_MAIN_TOUCHED`). 실행이 06:10~06:40 KST에 걸치면 `stock-strategy-system/` 비교만 건너뛴다(`SKIPPED_AUTO_CORE_WINDOW`, fail-closed가 아닌 예외).
- 재시도: 전체 1회(테스트 실패·Judge FAIL만), 같은 worktree에서, ①부터 전부 다시.

## 설치 (사용자 1번)

`powershell -ExecutionPolicy Bypass -File tools\register-dev-tasks.ps1` (`-PlanOnly`로 미리 보기). 두 작업 이름만 만들거나 덮어쓴다.
