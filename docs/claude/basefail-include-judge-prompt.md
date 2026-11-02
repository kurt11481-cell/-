---
id: basefail-include-judge-prompt
title: "basefail-include 독립 Judge (읽기 전용)"
date: 2026-11-02
class: "K3 수동 경로 Judge. Builder와 다른 세션, Read·Grep·Glob만(시험 실행이 필요하면 아래 줄만)"
source: "docs/claude/basefail-include-builder-prompt.md, docs/claude/basefail-cleanup-proposal-2026-11-02.md ②"
---

worktree의 diff(기준 커밋 대비)를 읽는다. 항목마다 PASS/FAIL과 근거(파일:행)를 표로 쓴다. 마지막 비지 않은 줄은 `VERDICT: PASS` 또는 `VERDICT: FAIL — <최소 수정 목록>`으로 쓴다.

1. tracked diff가 허용 파일 3개뿐이다: .worktreeinclude, .gitignore, docs/claude/basefail-include-report.md.
2. `.worktreeinclude`의 기존 2줄이 그대로 있다. 새 줄은 모두 정확한 경로(별표 없음)다. 경로는 모두 `workspace/outputs/…` 또는 `stock-strategy-system/market_snapshot.example.json`이고, 날짜는 2026-08이다. 실제 상태 파일(portfolio_state·alert_runtime_state 말고 새로 더한 stock-strategy-system 상태류)과 workspace/state/는 없다.
3. `.gitignore`는 지시문의 두 줄만 더해졌고, 다른 줄은 그대로다.
4. 새 경로가 모두 git 무시 대상이다(보고서 (e)). 본 저장소에서 tracked가 아니다.
5. 시험 파일·단언·devpipe 코드·정책·상태 변경이 없다.
6. 보고서 (c)에서 기준선 11건이 통과로 적혀 있다.
7. 보고서에 (a)~(e)가 있다. 복사한 파일 내용, 수량·금액·표지가 없다.

시험을 직접 돌려야 확인되는 항목만, 아래 형식으로 한 파일씩 돌린다(파일을 고치지 않는다):
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "<시험 파일 이름>.py"`
