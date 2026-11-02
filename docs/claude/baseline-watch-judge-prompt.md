---
id: baseline-watch-judge-prompt
title: "baseline-watch 독립 Judge (읽기 전용)"
date: 2026-11-01
class: "K3 수동 경로 Judge. Builder와 다른 세션, Read·Grep·Glob만(시험 실행이 필요하면 아래 한 줄만)"
source: "docs/claude/baseline-watch-builder-prompt.md, docs/claude/baseline-watch-proposal-2026-11-01.md"
---

worktree의 diff(기준 커밋 대비)를 읽고 아래 항목마다 PASS/FAIL과 근거(파일:행)를 표로 쓴다. 마지막 줄은 `VERDICT: PASS` 또는 `VERDICT: FAIL — <최소 수정 목록>`.

1. diff가 허용 파일 4개뿐이다(devpipe.py, test_dev_pipeline.py, tools/dev_pipeline/README.md, docs/claude/baseline-watch-report.md).
2. 1~9건 증가 = 경고만, 10건 이상 = STOP_BASELINE_REGRESSED, 문턱값 상수 10. 지시문과 다르면 FAIL.
3. 직전 기준선은 조상 커밋만 쓴다. 같은 python·method만 쓴다. 자기 자신을 빼고 computed_utc가 가장 늦은 것을 쓴다.
4. 캐시를 다시 쓰는 실행에서도 판정이 적용된다(옛 캐시 포함). 캐시 검사가 새 키로 거부하지 않는다.
5. accept 파일은 코드가 만들지 않는다. 그 기준 커밋 sha8에만 적용된다.
6. 기존 판정(새 실패, ran·skip, 권한 경로, merge_mode)과 기존 단언이 바뀌지 않았다. skip 추가 없음.
7. 추가된 시험이 지시문 목록 8개를 덮는다. 실제로 판정 분기를 거친다(빈 시험·항상 참 단언이 아님).
8. 주문·키움·정책·상태와 무관하고, 새 외부 호출·파일 삭제가 없다(캐시·실행 폴더 쓰기만).
9. 줄바꿈이 원래대로다(CRLF 파일 일괄 변환 없음).
10. 보고서에 (a)~(f)가 있고 수량·금액·표지가 없다.

시험을 직접 돌려야 확인되는 항목만, 이 한 줄을 쓴다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`. 파일을 고치지 않는다.
