---
id: gitattr-bytes-judge-prompt
title: "gitattr-bytes 독립 Judge (읽기 전용)"
date: 2026-11-02
class: "K3 수동 경로 Judge. Builder와 다른 세션, Read·Grep·Glob만(시험 실행이 필요하면 아래 줄만)"
source: "docs/claude/gitattr-bytes-builder-prompt.md, docs/claude/gitattr-bytes-proposal-2026-11-02.md"
---

worktree의 diff(기준 커밋 대비)를 읽는다. 항목마다 PASS/FAIL과 근거(파일:행)를 표로 쓴다. 마지막 비지 않은 줄은 `VERDICT: PASS` 또는 `VERDICT: FAIL — <최소 수정 목록>`으로 쓴다.

1. diff가 허용 파일 3개뿐이다: .gitattributes, manage-us-stock-strategy/tests/test_gitattributes_authority_bytes.py, docs/claude/gitattr-bytes-report.md.
2. `.gitattributes`에서 기존 줄이 그대로 있고, 새 `-text` 4줄이 지시문과 글자까지 같다.
3. 맨 뒤 `text` 예외 7줄이 지시문의 7개 경로와 같다. `workspace/policies/**` 전체, `assets/**`, `integrated_identity_session_activation.json`에 거는 줄이 없다.
4. 새 시험이 `git check-attr`로 대표 4개 = unset, 예외 1개 = set을 실제로 확인한다. skip·항상 참 단언이 없다.
5. 기존 시험 파일·단언 변경이 없다.
6. 보고서 (c)에서 기존 실패 16건이 통과로 적혀 있다. 보고서에 (a)~(e)가 있고 수량·금액·표지가 없다.
7. 새 외부 호출·파일 삭제가 없다. 주문·키움·정책 내용·상태와 무관하다.

시험을 직접 돌려야 확인되는 항목만, 아래 줄을 쓴다(파일을 고치지 않는다):
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_gitattributes_authority_bytes.py"`
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_v2_6_7_session_aware_kiwoom_priority.py"`
