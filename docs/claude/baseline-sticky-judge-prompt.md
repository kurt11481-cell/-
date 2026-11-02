---
id: baseline-sticky-judge-prompt
title: "baseline-sticky 독립 Judge (읽기 전용)"
date: 2026-11-02
class: "K3 수동 경로 Judge. Builder와 다른 세션, Read·Grep·Glob만(시험 실행이 필요하면 아래 한 줄만)"
source: "docs/claude/baseline-sticky-builder-prompt.md, docs/claude/baseline-sticky-proposal-2026-11-02.md"
---

worktree의 diff(기준 커밋 대비)를 읽고 항목마다 PASS/FAIL과 근거(파일:행)를 표로 쓴다. 마지막 비지 않은 줄은 `VERDICT: PASS` 또는 `VERDICT: FAIL — <최소 수정 목록>`.

1. diff가 허용 파일 4개뿐이다(devpipe.py, test_dev_pipeline.py, tools/dev_pipeline/README.md, docs/claude/baseline-sticky-report.md).
2. 멈춘 기준선(added ≥ BASELINE_ROSE_STOP, 표식 없음)만 후보에서 빠진다. 표식 있는 것·1~9건 경고 기준선·키 없는 옛 캐시는 남는다.
3. 조상·python·method·정렬 조건과 문턱값이 그대로다.
4. evaluate_tests 판정, 경고·멈춤 이름, 표식 이름·위치, dev-merge 경로가 그대로다.
5. 표식 파일을 코드가 만들지 않는다.
6. 추가 시험 5개가 지시문 목록을 덮고, 실제로 필터 분기를 거친다(빈 시험·항상 참 단언 아님). 기존 단언·skip 변경 없음.
7. 새 외부 호출·파일 삭제가 없다. 주문·키움·정책·상태와 무관하다.
8. 줄바꿈이 원래대로다(CRLF 일괄 변환 없음).
9. 보고서에 (a)~(e)가 있고 수량·금액·표지가 없다.

시험을 직접 돌려야 확인되는 항목만, 이 한 줄을 쓴다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`. 파일을 고치지 않는다.
