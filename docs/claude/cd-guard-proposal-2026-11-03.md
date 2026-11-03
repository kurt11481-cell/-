---
id: cd-guard-proposal-2026-11-03
title: "commit-docs가 권한 문서(헌법·자동화 재설계)를 사람 확인 없이 커밋하지 않게 하기 — K3 수정안 (CD-1)"
date: 2026-11-03
status: "사장 승인됨(아래 결정 기록). 실행은 사장실 한 줄 뒤 실행 스레드"
source: "docs/claude/code-review-pipeline-2026-11-01.md 3차 CD-1, 사장 카드 '셋 다 진행'(2026-11-03 21:48:48 KST)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책 내용·상태·일지·원장 쓰기 없음"
---

## 한 줄 결론
tools/commit-docs.ps1이 tools/dev_pipeline/authority-paths.txt의 docs/claude 줄을 읽게 한다. 지금 해당하는 문서는 헌법 constitution-v*.md와 automation-redesign-2026-10-10.md다. 이 문서가 든 _pending 파일은 자동 실행(23:30·개발 큐)에서 커밋하지 않고 HOLD로 남긴다. 사장이 대화형 PowerShell에서 `.\tools\commit-docs.ps1 -ApproveProtected`를 실행하고 Enter를 한 번 누를 때만 커밋한다.

## 확인한 것
- commit-docs.ps1 44행의 경로 검사는 세 가지뿐이다. docs/claude 아래인지, `..`이 없는지, _pending이 아닌지다.
- authority-paths.txt의 docs/claude 줄은 3개다. 21행 automation-redesign-2026-10-10.md, 64행 card-evidence-registry.json, 68행 constitution-v*.md다. 개발 큐 작업은 이 경로를 바꾸면 NEEDS_APPROVAL로 멈춘다. 그러나 스레드 문서 쓰기나 23:30 자동 커밋으로 들어오는 경로는 막지 않는다.
- card-evidence-registry.json은 막지 않는다. CLAUDE.md 48~51행에 따라 카드를 바꾸거나 수락한 대화형 세션이 같은 세션에서 갱신하고 커밋한다. 이것까지 막으면 카드를 수락할 때마다 사장이 PowerShell을 한 번 더 돌려야 한다.
- docs/claude/dev-runs/는 막지 않는다. devpipe가 결과 요약을 쓰고 _pending을 만들어 commit-docs로 커밋하기 때문이다(devpipe.py 1903~1906행).

## 바꿀 내용 (안)
1. commit-docs.ps1이 authority-paths.txt를 읽는다. 주석과 빈 줄은 뺀다. `docs/claude/`로 시작하는 줄만 쓰고, `docs/claude/card-evidence-registry.json`은 뺀다. glob 규칙은 authority-paths.txt 4행을 따른다. `*`는 한 폴더 안, `**`는 폴더를 건너고, 대소문자는 가리지 않는다.
2. authority-paths.txt를 못 읽거나 해석이 안 되면 그 실행에서는 모든 _pending 파일을 HOLD로 둔다(fail closed).
3. 바뀐 경로 중 하나라도 보호 목록에 맞는 _pending 파일은 처리하지 않는다. `HOLD <파일>: protected docs need .\tools\commit-docs.ps1 -ApproveProtected` 줄을 쓰고, 그 _pending 파일은 지우지 않는다. 문제 수에 넣는다(exit 1). 다른 _pending 파일은 지금처럼 처리한다.
4. `-ApproveProtected`일 때는 dev-merge.ps1 39~85행과 같은 대화형 확인을 거친다. 리다이렉트가 없어야 하고, ConsoleHost여야 하고, UserInteractive여야 하고, 두 표준 핸들이 콘솔이어야 한다. 그다음 HOLD 대상 목록을 보여 주고 Enter 한 번을 받는다. 하나라도 안 되면 `STOP_NOT_INTERACTIVE`를 쓰고 아무것도 커밋하지 않는다.
5. -DryRun은 HOLD 판정까지 보여 주고 아무것도 바꾸지 않는다.
6. 파일은 ASCII만 쓴다(9행, test_dev_pipeline 1695행).

## 바꾸지 않는 것
devpipe·dev-queue·run-docs-commit·authority-paths.txt 내용, 다른 docs/claude 경로의 흐름, 23:30 예약.

## 사장 손이 늘어나는 곳
헌법 새 판이나 자동화 재설계 문서를 커밋할 때만 PowerShell 1회가 는다. 헌법 개정은 이미 사장 직접 입력이 필요한 일이다(constitution-location). 평소 운영에는 늘지 않는다.

## 경로
tools/ 변경이라 **K3 수동 경로**를 거친다. 순서는 다음과 같다.
1. 사장 카드(받음)
2. 사장실 한 줄 "commit-docs 보호 실행해"
3. 실행 스레드 Builder(지시문 docs/claude/cd-guard-builder-prompt.md)
4. 별도 Judge(cd-guard-judge-prompt.md, 마지막 줄 `VERDICT: PASS`)
5. 사장 PowerShell 병합

되돌리기: 커밋 1개를 revert한다.

## 사장 결정 기록 (2026-11-03)
- 카드: cmsg_0137MRzn9nuDvvQmVxm6WeX9NQaebhrHGyYfpP6G8BQFus. 이 스레드가 올린 카드이고, 질문은 "남은 작은 수정 3건을 어떻게 진행할까요?"였다. 선택지 B는 "③-a·RI-1에 더해 CD-1 commit-docs 보호 목록을 K3로 진행"이다.
- 고른 항목: "셋 다 진행" (option_index 1)
- 누른 계정: user_01KuMGKfZu1SBYxtMmg4vAiH (프로젝트 소유자 = 사장)
- 시각: 2026-11-03 21:48:48 KST (harness wake 원문 기준)
- 범위: 이 수정안 1건, 2026-11-03 하루, 1회. 날짜가 넘어가면 시작 직전에 같은 수정안으로 카드를 다시 받는다. 병합은 별도 사장 결정이다.
- 같은 카드로 진행한 나머지 둘:
  - ③-a: diff-v3.2-v3.3.txt를 .diff로 이름만 바꿈. sha256이 같음을 확인했다(b2a48ed5…).
  - RI-1: 개발 큐 ri1-session.
