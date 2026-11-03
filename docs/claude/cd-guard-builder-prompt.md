---
id: cd-guard-builder-prompt
title: "commit-docs 권한 문서 HOLD — Builder (K3, CD-1)"
date: 2026-11-03
class: "K3 수동 경로(tools/ 보호 경로). 회사PC worktree Builder(Opus) → 별도 읽기 전용 Judge → 병합은 사장 결정 뒤 사장 PowerShell"
source: "docs/claude/cd-guard-proposal-2026-11-03.md, 사장 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9NQaebhrHGyYfpP6G8BQFus '셋 다 진행' 2026-11-03 21:48:48 KST"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 목표
수정안 docs/claude/cd-guard-proposal-2026-11-03.md "바꿀 내용" 1~6을 tools/commit-docs.ps1에 구현한다.

## 바꿀 파일 (이 3개만)
- tools/commit-docs.ps1
- manage-us-stock-strategy/tests/test_dev_pipeline.py (글자 검사 시험만 추가)
- docs/claude/cd-guard-report.md (보고)

## 구현 요구
1. 보호 목록은 tools/dev_pipeline/authority-paths.txt에서 읽는다. 목록을 commit-docs에 복사해 적지 않는다. 쓰는 줄은 `docs/claude/`로 시작하는 줄이고, `docs/claude/card-evidence-registry.json` 한 줄은 정확히 그 문자열로 뺀다.
2. glob을 정규식으로 바꾼다. `**`는 `.*`, `*`는 `[^/]*`, 나머지는 이스케이프한다. 앞뒤를 고정하고(^…$) 대소문자는 가리지 않는다. 비교할 때 경로의 `\`는 `/`로 바꾼다.
3. 판정은 이 _pending 파일에서 실제로 바뀐 경로($changed)에 한다. 하나라도 맞으면 HOLD다.
   - -ApproveProtected가 없으면 HOLD 줄을 쓰고 `$failed++`를 한 뒤 다음 파일로 간다. _pending 파일은 지우지 않는다.
   - -ApproveProtected가 있으면 아래 4번 확인을 한 번 통과한 뒤에만 커밋한다.
4. -ApproveProtected 확인은 dev-merge.ps1 39~85행과 같은 방식이다.
   - [Console]::IsInputRedirected·IsOutputRedirected, $Host.Name, [Environment]::UserInteractive를 본다.
   - GetConsoleMode로 두 표준 핸들을 확인한다. Add-Type 형식 이름은 dev-merge와 겹치지 않게 한다.
   - HOLD 대상 경로 목록을 출력하고, Enter를 한 번 받는다. 입력 내용은 비교하지 않는다. $null이거나 오류면 STOP_NOT_INTERACTIVE로 끝낸다.
   - 확인은 실행당 1회만 하고, 대상이 없으면 묻지 않는다. 실패하면 `STOP_NOT_INTERACTIVE`를 출력하고 아무것도 커밋하지 않은 채 exit 2로 끝낸다.
5. authority-paths.txt를 못 읽거나 docs/claude 줄이 하나도 없으면, 모든 _pending 파일을 HOLD로 처리한다(fail closed). -ApproveProtected로도 넘어가지 않는다.
6. -DryRun은 PLAN과 HOLD를 모두 보여 주고, 아무것도 스테이징하거나 커밋하지 않는다.
7. 머리 주석(1~11행)에 새 규칙 3줄 이내와 사용법 1줄을 더한다. 파일은 ASCII만 쓴다. 기존 안전 문구는 그대로 둔다(test_dev_pipeline 1696~1697행이 검사하는 글자).
8. test_dev_pipeline.py에는 `test_docs_commit_runner_keeps_commit_docs_safety` 옆에 글자 검사 시험 1개만 더한다. 검사하는 글자는 `authority-paths.txt`, `-ApproveProtected` 또는 `ApproveProtected`, `HOLD`, `STOP_NOT_INTERACTIVE`, `card-evidence-registry.json`이다. 다른 시험은 바꾸지 않는다.

## 시험
- 이 한 줄을 글자 그대로 쓴다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`
- worktree 안에서만 아래를 확인한다.
  - 임시 _pending 파일 2개를 만든다. 하나는 docs/claude/constitution-v1.4.0.md에 공백 1줄을 더한 복사 상태를 가리키고, 하나는 일반 문서를 가리킨다.
  - `powershell -NoProfile -File tools\commit-docs.ps1 -DryRun`을 실행해 HOLD 1개와 PLAN 1개가 나오는지 본다.
  - 끝나면 임시 _pending 파일과 헌법 파일 변경을 되돌린다. git status에 남으면 안 된다.
  - -DryRun이 아닌 실행, -ApproveProtected 실행은 하지 않는다.
- 전체 스위트는 돌리지 않는다. git은 status·diff·log·checkout -- <그 헌법 파일>만 쓴다.

## 지켜야 할 것
- 위 3개 파일 밖의 tracked 파일은 바꾸지 않는다. authority-paths.txt·devpipe·dev-queue·run-docs-commit·.claude·정책·상태는 금지다.
- 줄바꿈은 지킨다(commit-docs.ps1, test_dev_pipeline.py 모두 i/lf).
- 주문·키움·일지·원장·예약과 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음. 비밀(.env*·토큰·계좌번호)을 읽지 않는다.
- 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/cd-guard-report.md
- (a) 바꾼 줄(파일:행)
- (b) 보호 목록으로 읽힌 패턴(지금 2개 예상: automation-redesign·constitution-v*)
- (c) DryRun 확인 출력(HOLD·PLAN 줄만)
- (d) 시험 결과 마지막 3줄
- (e) `git status --short`

수량·금액·주문 표지 문자열은 적지 않는다("표지 없음").
