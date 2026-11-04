---
id: cd-guard-report
title: "commit-docs 권한 문서 HOLD — Builder 보고 (K3, CD-1)"
date: 2026-11-04
source: "docs/claude/cd-guard-builder-prompt.md, docs/claude/cd-guard-proposal-2026-11-03.md, 사장 카드 '승인, 오늘 진행' 2026-11-04 08:04:23 KST"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
base: "aad5fbe0db85ffe66af4caf71b2cf6c80a851bb6 (codex/master-recovery-expansion), worktree .claude/worktrees/cd-guard, 브랜치 worktree-cd-guard"
---

## 한 줄 결론
commit-docs.ps1이 authority-paths.txt의 docs/claude 줄(카드 증거 원장 제외)을 읽어, 그 문서를 바꾼 _pending 파일은 HOLD로 남긴다. -ApproveProtected는 대화형 콘솔 확인 + Enter 1회 뒤에만 커밋한다. 커밋·push·병합은 하지 않았다.

## (a) 바꾼 줄 (파일:행, 새 파일 기준)
- tools/commit-docs.ps1:9-11 — 머리 주석 새 규칙 3줄
- tools/commit-docs.ps1:15 — 사용법 1줄(-ApproveProtected)
- tools/commit-docs.ps1:17 — param에 `[switch]$ApproveProtected` 추가
- tools/commit-docs.ps1:38-58 — 보호 목록 읽기(authority-paths.txt, `docs/claude/` 줄만, card-evidence-registry.json 제외), glob→정규식(`**`=`.*`, `*`=`[^/]*`, 나머지 이스케이프, ^…$, IgnoreCase), 못 읽거나 0개면 fail closed
- tools/commit-docs.ps1:60-104 — 1차 루프: 기존 경로 검사·$changed 계산은 그대로, $changed 경로(`\`→`/`)에 HOLD 판정. HOLD면 줄 출력 + `$failed++`, _pending 파일은 지우지 않음. fail closed면 -ApproveProtected와 무관하게 HOLD
- tools/commit-docs.ps1:106-153 — -ApproveProtected 확인(실행당 1회, 대상이 있을 때만, -DryRun이면 묻지 않음): 리다이렉트·ConsoleHost·UserInteractive, GetConsoleMode 두 핸들(형식 이름 CommitDocsConsoleHandles), 대상 목록 출력, Enter 1회(내용 비교 없음, $null·오류면 실패). 실패 시 `STOP_NOT_INTERACTIVE`, 아무것도 커밋하지 않고 exit 2
- tools/commit-docs.ps1:155-177 — 2차 루프: 기존 PLAN·git add·commit 흐름 그대로(계획된 파일만)
- manage-us-stock-strategy/tests/test_dev_pipeline.py:1700-1704 — `test_commit_docs_holds_protected_docs` 글자 검사 시험 1개 추가(`test_docs_commit_runner_keeps_commit_docs_safety` 바로 뒤). 다른 시험은 바꾸지 않음
- 기존 안전 문구(`'^docs/claude/[^/]'`, `git diff --cached --quiet`, `STOP: other changes are already staged`, `Nothing was pushed.`)는 그대로 둠. 파일은 ASCII만, 줄바꿈은 i/lf(작업 사본 w/crlf, 기존과 같음)

## (b) 보호 목록으로 읽힌 패턴 (2개)
- `docs/claude/automation-redesign-2026-10-10.md` (authority-paths.txt 21행)
- `docs/claude/constitution-v*.md` (authority-paths.txt 68행)
- 뺀 줄: `docs/claude/card-evidence-registry.json` (64행)

## (c) DryRun 확인 출력 (HOLD·PLAN 줄만)
임시 _pending 2개(헌법 constitution-v1.4.0.md에 빈 줄 1개 추가 / 일반 문서 cd-guard-report.md), `powershell -NoProfile -File tools\commit-docs.ps1 -DryRun`, worktree 안에서만:
```
HOLD  zz-cdguard-protected.txt: protected docs need .\tools\commit-docs.ps1 -ApproveProtected
PLAN  zz-cdguard-plain.txt: "test: plain doc (temporary, cd-guard DryRun)"
```
exit 1. 끝난 뒤 헌법 파일은 `git checkout --`로, 임시 _pending 파일·폴더는 삭제로 되돌림. -DryRun이 아닌 실행, -ApproveProtected 실행은 하지 않음.

## (d) 시험 결과 마지막 3줄
`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`
```
Ran 151 tests in 141.926s

OK
```
(첫 실행은 test_ps1_ascii_and_crlf 1건 실패 — 작업 사본을 LF로 썼기 때문. CRLF 작업 사본으로 고친 뒤 통과. 색인은 i/lf 그대로.)

## (e) git status --short
```
 M manage-us-stock-strategy/tests/test_dev_pipeline.py
 M tools/commit-docs.ps1
?? docs/claude/cd-guard-report.md
```

## 표지
수량·금액·주문 표지 없음.

## 결론을 바꿀 조건
Judge가 -ApproveProtected 확인 순서(1차 루프에서 HOLD 판정 → 확인 → 커밋)나 fail closed 범위가 수정안 2·4번과 다르다고 보면 다시 고친다.
