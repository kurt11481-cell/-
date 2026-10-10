---
id: redesign-t3-judge2-report-2026-10-10
title: 재설계 T3 2차 Judge 판정 — r2(F1~F3 + O1·O2·O6) 확인
date: 2026-10-10
class: 일반 변경(재설계 A5) — 1차 Judge FAIL 뒤 같은 Builder 최소 수정의 독립 재확인
judge_prompt: docs/claude/redesign-t3-judge2-prompt-2026-10-10.md
judge1_report: docs/claude/redesign-t3-judge-report-2026-10-10.md
target: .claude/worktrees/redesign-t3 (브랜치 worktree-redesign-t3, HEAD = base d7d5292, 미커밋 — 추적 수정 2 + 새 파일 13)
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: Cowork(병합 판단) · 관제판 redesign-t3
---

# PASS

- 1차 FAIL 사유 F1~F3이 모두 고쳐졌다. 선택 항목 O1·O2·O6도 들어갔다. 1차의 PASS 근거(J2·J3a·J6 포함)는 깨지지 않았다. 병합을 막는 것은 없다.
- 아래 "의견"은 병합 조건이 아니다. 첫 시험 뒤 후속으로 판단한다.
- 확인 방법: Builder 보고는 증거로 쓰지 않았다.
  - 직접 확인한 것: `git status`·`git diff d7d5292`, 바뀐 파일 원문, worktree 테스트 직접 실행, 스키마 감사, PowerShell 파서, `claude --version`·`--help`, 공식 문서 3쪽(permissions·permission-modes·tools-reference, 읽기만).
  - 명령줄 확인(K2): 임시 폴더 스크립트로 확인했다. dev-run.ps1은 실행하지 않았다. AST로 상수만 꺼내 Start-Builder와 같은 문자열을 만들고, claude 대신 argv를 찍는 python으로 `cmd /d /s /c`를 돌렸다.
  - 실행하지 않은 것: dev-run·dev-merge·dev-queue, 모델을 부르는 `claude -p`, 작업 등록, 키움. 비밀 파일과 사용자 설정 파일은 읽지 않았다.
  - worktree에 새 파일을 만들지 않았다(PYTHONDONTWRITEBYTECODE=1). 실행 뒤 무시 파일은 253개 그대로이고, 17:00 이후 시각의 파일은 0개다.
- 한계: r1 새 파일은 미커밋이라 r1과 바이트 diff를 할 수 없었다. 대신 두 가지로 확인했다.
  - 수정 시각: 1차 보고(16:16) 뒤에 바뀐 파일은 dev-run.ps1·dev-queue.ps1·devpipe.py·authority-paths.txt·README.md·test_dev_pipeline.py와 보고·r2 파일뿐이다.
  - 줄 번호: 1차 보고의 devpipe 줄 인용이 정확히 +2(표지), +4(O2), +20(O1) = +26만큼 밀렸다. 그 밖의 블록 길이 변화는 없다.

## 판정표

`devpipe` = tools/dev_pipeline/devpipe.py, `test` = manage-us-stock-strategy/tests/test_dev_pipeline.py. 줄 번호는 worktree 파일 기준이다.

| # | 판정 | 근거 |
|---|---|---|
| K1 F1 | PASS | dev-run.ps1:32-39 `$BuilderAllowedTools` 16개가 모두 `Bash(…)`·`PowerShell(…)`이다. 이름만 있거나 경로를 묶은 Read·Edit·Write·Grep·Glob 규칙은 0개다. `--tools`는 그대로다(:27 `'Read,Edit,Write,Grep,Glob,Bash,PowerShell'`, :242). 문서 근거는 맞다. ① 읽기 승인: permissions "Read-only … No, within the working directory and additional directories". tools-reference "Read, Grep, and Glob, still prompt for paths outside the working directory". ② 편집 승인: permission-modes "acceptEdits … auto-approval applies only to paths inside your working directory or additionalDirectories". ③ worktree 위치: 보호 디렉터리 `.claude`의 예외에 "Claude's own git worktrees under `.claude/worktrees/`"가 있다. 그래서 worktree 안 편집은 그대로 승인된다. ④ 거절: `--permission-prompts none`은 "anything that would prompt is denied automatically"(help 원문). ⑤ 추가 근거: 문서상 출력·입력 리디렉션(`> f`, `< f`)은 Edit·Read allow 규칙으로 검사된다. 그래서 이름만 있는 규칙을 뺀 것이 `git diff > 밖경로`도 함께 막는다. 정적 단언은 test:830-833에 있다. README:76이 맞다. |
| K2 F2 | PASS | dev-run.ps1:41-45 `$BuilderDisallowedTools`에 `mcp__*`, `Bash/PowerShell(git *--output*)`, `Bash/PowerShell(git *--no-index*)`가 있고, :242에서 Builder 명령이 쓴다. Judge 명령(:257-259)은 그대로 `"mcp__*"`다. 문서 근거: "Rules are evaluated in order: deny, then ask, then allow … An allow rule can't carve an exception out of a deny rule". `*`는 가운데에도 쓸 수 있고(문서 표에 `git log --output=<file>`가 예시로 있다), PowerShell 규칙도 같은 모양이다. 명령줄 실측: 인자 44개로 나뉜다. deny 5개·allow 16개가 각각 한 인자로 온전하고, 와일드카드 확장은 없다. help의 "Comma or space-separated … (e.g. "Bash(git *) Edit")"대로 괄호 안 공백은 한 규칙으로 읽힌다. 정적 테스트는 test:837-845다. 부작용: 문서상 Bash 범위 deny는 PowerShell 도구를 끈다. 다만 settings 파일에 범위 PowerShell 규칙이 있으면 끄지 않는다. 프로젝트 settings.json에 `PowerShell(*dev-run.ps1*)` 등이 이미 있으므로 PowerShell 도구는 켜진 채 남는다고 읽힌다. 꺼지더라도 Bash가 남으므로 좁히는 방향이다. |
| K3 F3 | PASS | devpipe:98-99에 7개 표지가 있다: 기존 2개 + `quantity_authority`·`execution_quantity`·`watchlist_approved`·`active_universe_approved`·`new_buy_instrument_approved`. 대소문자 무시로 removed 줄을 본다(:758-762). authority-paths.txt:60-61에 2개가 추가됐고, 두 파일 모두 있다. 각 파일에 승인 const false 줄(schema:19-21, 24)과 `False` 줄(build…py:35-37)이 있다. 테스트 test:412-427: 표지 5개 각각 const를 바꾸면 `REMOVED_LINE:<표지>`, class = authority다. 이 픽스처 파일은 권한 경로 밖이라 표지만으로 오르는 것을 검사한다. 올리기만 한다(escalate :773-774, 내리는 코드 없음). F3 d 재계산(git ls-files, tests/ 제외): 목록 안 29개. 밖 382개(파이프라인과 같은 대소문자 무시 기준) = docs 113 · workspace 101 · schemas 72 · scripts 60 · 스킬 기타 9 · 보호 27. Builder 수 377과의 차이 5개는 두 가지다. 대문자로만 쓴 workspace 보고서 3개와, 이름이 `test_only_*`인 scripts 2개(Builder가 테스트로 뺀 것으로 보임)다. 결론에는 영향이 없다. 줄 표지로 충분한지는 의견 N1. |
| K4 O1 | PASS | devpipe:1193-1210 `refresh_include_snapshot`이 경로 목록은 그대로 둔다(`include_candidates(repo, base)` :1005-1013). sha256만 다시 재고, init 값은 `include_snapshot_init`에 남긴다(setdefault). 호출은 dev-run.ps1:323-324 한 곳뿐이다. 기준선(:318) 뒤, Builder 1회차 Start-Builder(:327) 바로 앞이다. 실패하면 그 status로 끝난다. 수정 회차(Invoke-FixPass :278-287)와 그 밖의 어느 곳도 다시 재지 않는다. include_snapshot을 쓰는 곳은 :1173(init)과 :1201-1203뿐이다. 예외 판정 `protected_violations`(:665-674)는 바뀌지 않았다(경로 ∈ 스냅샷 + sha256 정확 일치). 따라서 예외 범위는 넓어지지 않았다. ensure_baseline(:883-918)은 스냅샷의 키(경로)만 쓴다. 기준선은 init 값(:1187), 병합 rebase는 다시 잰 값(:1593)을 쓰지만 같은 목록이라 어긋나지 않는다. 테스트 test:429-451: init 값이면 Stop이다. 다시 재면 STOP 아님이고, worktree 사본만 바꾸면 STOP_PROTECTED다. |
| K5 O2·O6 | PASS | O2: devpipe:563-566. 원 출력의 `expected failures=N`(파서 :482-486)이 기준선보다 크면 `EXPECTED_FAILURES_INCREASED:<뒤>><기준>`이다. reasons에 들어가므로 RETRYABLE이고, unexpected successes(:560-562) 바로 옆이다. 테스트 test:293-302(증가 → 사유, 같음 → 사유 없음). O6: dev-queue.ps1:19-20 `$CommitDocsLimitSeconds = 900`, `$DevRunLimitMinutes = 340`, 사용은 :129, :143. 900/60 + 340 + 5 = 360 = register-dev-tasks.ps1:34 `$queueLimitHours = 6` × 60. 정적 테스트 test:847-856은 숫자를 세 파일에서 읽어 단언하고, 직접 기입을 금지한다. |
| K6 회귀 | PASS | 범위: r2에서 바뀐 것은 위 6개 파일 + 보고 + r2 지시문뿐이다. dev-merge.ps1·register-dev-tasks.ps1·run-docs-commit.ps1·builder-rules.md·judge-prompt.md는 15:38 이후 그대로다. 추적 diff는 1차와 같다: settings.json +12/−0(41줄 모두 CRLF), .gitignore +2/−0(159줄 모두 CRLF). `--ignore-cr-at-eol` 결과도 같다. tools/commit-docs.ps1 diff는 0이다. 위생: .ps1 6개(commit-docs 포함) 비ASCII 0, 전부 CRLF, 파서 오류 0. 새 코드·문서 파일은 CRLF이고 BOM이 없다. 예외: r2 지시문 1개가 LF다(의견 N4). J2: 보호 상수 devpipe:78-93는 줄도 내용도 같다. 기준 커밋 읽기(:1153-1157, :1509), 복사 예외(:665-674)도 그대로다. J3a: bypass·dangerously 문자열이 tools/ 전체에 0이다. Builder는 acceptEdits + none(:240), Judge는 Read·Grep·Glob + mcp deny + strict(:257-259)다. J6: verify_for_merge :1489-1519, do_merge :1604-1658(ff-only :1644, 되돌림은 worktree만 :1646-1649)이다. 1차 인용에서 +26만 밀렸다. worktree 무시 보호 파일 3개 sha256 = 메인 사본이다. |
| K7 테스트 | PASS | worktree 직접 실행(Windows git 2.56, Python 3.13.15): `test_dev_pipeline*` **Ran 86, OK**(107.6초). 86 = 81 + 새 5개: test:293, :412, :429, :837, :847. 같은 실행에서 `test_auto_core*` Ran 89 OK, `test_reconcile_broker_state*` Ran 56 OK, `test_portfolio_exposure_judge_fixes*` Ran 29 OK다. 전체 스위트(test-runner, PYTHONUTF8=1·PYTHONIOENCODING=utf-8·PYTHONDONTWRITEBYTECODE=1): **Ran 2670 tests in 315.628s · FAILED (failures=19, errors=9, skipped=2)**. 원본 stderr에서 직접 뽑은 실패 블록 28개를 기준 28개와 (종류·메서드·모듈)로 하나씩 맞췄다: **28/28, 새 실패 0, 사라진 것 0**(subTest 4개 포함). Ran 2665 → 2670(+5)이고 skipped 2 → 2다. 스키마 감사 `"status": "PASS"`, exit 0. |

## 조건

없음.

## 의견 (병합 차단 아님)

- **N1 줄 표지의 빈틈**: 새 5개 표지는 지우거나 바꾼 줄만 본다. 그래서 다음은 general로 남는다.
  - 새 줄 추가: 예) 새 코드나 산출물에 `"watchlist_approved": true`, `quantity_authority = "full"`, `execution_quantity: 5`를 넣는 경우. 추가 줄 검사는 주문 표지·`order_authority … true`·`kill_switch`뿐이다(:748-757).
  - 표지 줄을 건드리지 않는 논리 변경: 예) 목록 밖 검증기의 비교식만 바꾸는 경우.
  - 지금은 Judge의 class_ok 확인(G 항목)이 뒷받침한다. 실제 상태·정책은 보호 경로이고, 주문 경로는 권한 경로다. 그래서 병합을 막을 일은 아니다.
  - 첫 시험 뒤 파이프라인을 고칠 때 추가 줄 정규식 1개를 권한다(올리기만): `(watchlist|active_universe|new_buy_instrument)_approved … [:=] … true`, `quantity_authority … [:=]` 값이 none이 아님, `execution_quantity … [:=]` 값이 null/None이 아님.
  - 반대로 `quantity_authority`가 356개 파일에 있어 오탐(NEEDS_APPROVAL, 사용자 1번)이 늘 수 있다. 안전 쪽이다.
- **N2 문서**: README:80 "테스트" 줄과 judge-prompt.md에는 `expected failures` 증가가 아직 없다. 코드·테스트는 맞다. 다음 파이프라인 수정 때 한 줄을 맞춘다.
- **N3 Builder 보고 수치 2개**(판정에 쓰지 않음):
  - F3 d 밖 377 → 파이프라인 기준으로는 382다(K3).
  - O6 "dev-run 내부 상한 합 최악 약 300분"은 상수 합과 다르다. 기준선 70 + Builder 120 + 검사 100 + Judge 45 + 수정 60 + 검사 100 + Judge 45 ≈ 540분이다(1차 J12-12와 같음). 340분을 넘으면 dev-queue가 STOP_QUEUE_TIMEOUT으로 끝내고(fail-closed), 죽은 잠금은 다음 실행이 정리한다.
- **N4 줄바꿈**: worktree의 r2 지시문(docs/claude/redesign-t3-builder-r2-2026-10-10.md, Cowork 작성)만 LF다(58줄). `core.autocrlf=true`라 색인에는 LF로 들어가므로 문제없다. 일괄 변환하지 않는다.
- **N5 첫 시험에서 함께 볼 것**(1차 알려진 후속에 더함):
  - F1 뒤 헤드리스 Builder가 worktree 안에서 Read·Grep·Glob을 묻지 않고 쓰는지, Edit·Write가 acceptEdits로 승인되는지 본다. 안 되면 STOP_NO_CHANGES 또는 BLOCKED로 끝난다(fail-closed).
  - `-p --worktree`의 작업 폴더가 worktree인지 본다(1차 후속 1).
  - PowerShell 도구가 켜져 있는지 본다(K2 부작용).
  - deny 규칙은 문서상 보안 경계가 아니다(`git -c …`, 옵션 약어 등 다른 형태). 저장소 밖 쓰기는 사후 검사가 못 잡는다는 잔여 위험(1차 O3)은 그대로다.
