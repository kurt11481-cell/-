---
id: cd-guard-judge-prompt
title: "cd-guard 독립 Judge (읽기 전용)"
date: 2026-11-03
class: "K3 수동 경로 Judge. Builder와 다른 세션, Read·Grep·Glob만(시험 실행은 아래 줄만)"
source: "docs/claude/cd-guard-builder-prompt.md, docs/claude/cd-guard-proposal-2026-11-03.md"
---

worktree의 diff(기준 커밋 대비)를 읽는다. 항목마다 PASS/FAIL과 근거(파일:행)를 표로 쓴다. 마지막 비지 않은 줄은 `VERDICT: PASS` 또는 `VERDICT: FAIL — <최소 수정 목록>`으로 쓴다.

1. tracked diff가 허용 파일 3개뿐이다: tools/commit-docs.ps1, manage-us-stock-strategy/tests/test_dev_pipeline.py, docs/claude/cd-guard-report.md.
2. 보호 목록은 authority-paths.txt에서 읽고, docs/claude 줄만 쓰며, card-evidence-registry.json 한 줄만 뺀다. 복사한 목록이 없다.
3. glob 변환이 맞다(** / * / 이스케이프 / 앞뒤 고정 / 대소문자 무시). constitution-v1.4.0.md·automation-redesign-2026-10-10.md는 맞고, card-evidence-registry.json·dev-runs/x.md·active-decisions.md는 안 맞는다.
4. HOLD는 _pending 파일을 지우지 않고 문제 수에 넣는다. 다른 _pending 파일 처리는 그대로다.
5. authority-paths.txt를 못 읽거나 줄이 없으면 모두 HOLD다. -ApproveProtected로도 못 넘어간다.
6. -ApproveProtected 확인이 dev-merge.ps1 39~85행과 같은 수준이다(리다이렉트·ConsoleHost·UserInteractive·GetConsoleMode·Enter). 실패하면 아무것도 커밋하지 않는다.
7. -DryRun은 아무것도 스테이징·커밋하지 않는다. 기존 안전 문구가 있고(test_dev_pipeline 1696~1697행), 파일이 ASCII다.
8. 새 시험은 글자 검사 1개뿐이다. 다른 시험·단언·skip 변경이 없다.
9. 보고서에 (a)~(e)가 있고 수량·금액·표지가 없다. git status에 임시 파일이 없다.

시험이 필요하면 이 줄만 쓴다(파일을 고치지 않는다):
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`
