---
id: redesign-t3-builder-r2-2026-10-10
title: 재설계 T3 Builder 2회차 — Judge FAIL 최소 수정(F1~F3) + 선택 O1·O2·O6
date: 2026-10-10
class: T3와 같음(일반 변경). 범위·금지는 redesign-t3-builder-prompt-2026-10-10.md 2절 그대로
judge_report: 메인 체크아웃 docs/claude/redesign-t3-judge-report-2026-10-10.md (1차 FAIL, 16:3x KST) — 필요한 내용은 아래에 모두 옮겼다(읽으러 가지 않아도 된다)
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: T3 Builder(같은 worktree redesign-t3) · T3 2차 Judge(docs/claude/redesign-t3-judge2-prompt-2026-10-10.md, 메인 체크아웃)
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 같은 worktree `redesign-t3`(1회차 창이 열려 있으면 그대로) · 이유: 파이프라인 권한 상수 수정**

```
경계·금지: 1회차 지시문 2절 그대로. 추가로:
 - .claude/settings.json·.gitignore는 이번에 고치지 않는다(1회차 diff +12/−0, +2/−0 그대로 둔다).
 - dev-run.ps1·dev-merge.ps1·dev-queue.ps1 실행 금지(P9 deny가 이미 막는다). 모델을 부르는 claude -p 금지. 키움·비밀 금지.
 - tools/ 아래 편집은 P9 ask 때문에 승인 창이 뜬다 — 사용자가 승인한다(정상).
판단이 필요하면 BLOCKED.md를 worktree 루트에 쓰고 멈춘다.

F1 (필수) tools/dev-run.ps1 $BuilderAllowedTools(31줄)에서 이름만 있는 'Read','Edit','Write','Grep','Glob' 다섯 개를 뺀다.
   이유(1차 Judge J3b): 이름만 있는 규칙은 그 도구의 모든 사용과 맞아서 worktree 밖(메인 체크아웃의 상태·정책·run.json·devpipe.py, .env*)
   읽기·쓰기를 묻지 않고 승인한다. worktree 안 읽기는 원래 승인이 필요 없고 편집은 acceptEdits가 승인한다. 밖 경로는 묻기가 되고
   --permission-prompts none이 거절한다. 경로를 묶은 규칙(Read(/**) 등)도 넣지 않는다.
   --tools 목록(Read,Edit,Write,Grep,Glob,Bash,PowerShell)은 도구를 싣는 목록이라 그대로 둔다.
   함께: test_dev_pipeline.py test_builder_command_constants에 "allowedTools에 이름만 있는 Read|Edit|Write|Grep|Glob 규칙 없음" 단언 추가,
   tools/dev_pipeline/README.md '고정 상수' 줄 맞춤.
F2 (필수) Builder 명령의 --disallowedTools(235줄, 지금 "mcp__*")에 4개 추가:
   Bash(git *--output*), PowerShell(git *--output*), Bash(git *--no-index*), PowerShell(git *--no-index*)
   이유: allow의 git diff/log * 가 --output=<임의 경로>(쓰기)와 --no-index <임의 파일>(읽기)도 허용한다. deny가 allow보다 먼저 적용된다.
   Judge 명령(252줄)은 Bash가 없으므로 그대로. 정적 테스트 1개.
F3 (필수) 권한 표지 보강 — 올리기만:
   a. devpipe.py REMOVED_LINE_MARKERS(97줄)에 quantity_authority, execution_quantity, watchlist_approved, active_universe_approved,
      new_buy_instrument_approved 추가(수정·삭제된 줄은 removed 줄로도 나오므로 authority로 오른다).
   b. tools/dev_pipeline/authority-paths.txt에 manage-us-stock-strategy/schemas/candidate-discovery-proposal.schema.json,
      manage-us-stock-strategy/scripts/build_candidate_discovery_proposal.py 추가.
   c. check-tree 테스트 1개: 스키마의 승인 const 줄(예: "new_buy_instrument_approved": {"const": false})을 바꾸면 class = authority.
   d. 같은 5개 표지가 들어간 비테스트 파일 중 authority-paths 밖인 것을 grep으로 세어 보고에 적는다(줄 표지가 덮으므로 목록 추가는 b의 2개만).

선택(이번에 넣는다 — 파이프라인 파일은 나중에 다시 고치려면 기존 방식을 한 번 더 돌아야 하므로):
O1 include 스냅샷 시점: run.json include_snapshot을 init-run(기준선 전)이 아니라 Builder 1회차 시작 바로 앞에서 다시 잰다
   (devpipe 하위 명령 1개 또는 기존 명령 옵션, dev-run.ps1에서 Start-Builder 직전 호출). 수정 2회차는 1회차 스냅샷을 그대로 쓴다
   (worktree 사본은 1회차 worktree 생성 때 복사된 것이므로). ensure_baseline이 include_snapshot을 쓰는 곳(877·893줄)과 어긋나지 않게 하고,
   예외 범위(경로 목록·sha256 정확 일치)는 넓히지 않는다. 테스트 1개(기준선 뒤 메인 사본이 바뀌어도 다시 잰 값과 같으면 STOP 아님,
   worktree 사본만 바뀌면 STOP).
O2 expected failures 증가 = RETRYABLE(unexpected successes와 같은 방식, 558~559줄 옆). unittest 요약의 "expected failures=N" 파싱. 테스트 1개.
O6 dev-queue.ps1: commit-docs 상한(900초) + dev-run 상한 + 여유 5분 ≤ 작업 한도 360분이 되게 $DevRunLimitMinutes를 낮춘다(예: 340).
   상수 관계를 정적 테스트 1개로 고정.

하지 않는 것: O3(메인 체크아웃 변경 감시)·O4(heartbeat 읽기, 배포 때 Cowork)·O5(git 버전) — 첫 시험 뒤 판단.

완료 기준:
 - test_dev_pipeline* 전부 OK(새 테스트 포함), test_auto_core*·test_reconcile_broker_state*·test_portfolio_exposure_judge_fixes* OK.
 - 전체 스위트(test-runner, PYTHONUTF8=1·PYTHONIOENCODING=utf-8): 실패 id 집합 = 1회차 기준선 28개, Ran은 늘기만, 스키마 감사 PASS.
 - .claude/settings.json·.gitignore diff가 1회차와 같음. 새·바뀐 .ps1 ASCII·CRLF, PowerShell 파서 오류 0. 바뀐 기존 파일 CRLF 유지.
 - 바뀐 경로는 1회차 허용 경로 안 + 이 파일.
보고: docs/claude/redesign-t3-builder-report-2026-10-10.md 끝에 "## r2 (Judge FAIL 수정)" 절 추가 — F1·F2·F3·O1·O2·O6 각각 바꾼 파일:줄 한 줄,
F3 d의 grep 결과, 테스트 수치(대상·전체·기준선 대비), 남는 위험.
```
