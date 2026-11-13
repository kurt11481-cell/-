---
id: baseline-pyver-judge-prompt
title: "baseline-pyver 독립 Judge (읽기 전용)"
date: 2026-11-13
class: "K3 수동 경로 Judge. Builder와 다른 세션, Read·Grep·Glob만(시험 실행이 필요하면 아래 한 줄만)"
source: "docs/claude/baseline-pyver-builder-prompt.md, docs/claude/baseline-pyver-proposal-2026-11-13.md"
---

worktree의 diff(기준 커밋 대비)를 읽고 아래 항목마다 PASS/FAIL과 근거(파일:행)를 표로 쓴다. 마지막 비지 않은 줄은 `VERDICT: PASS` 또는 `VERDICT: FAIL — <최소 수정 목록>`이다.

1. diff가 허용 파일 4개뿐이다: devpipe.py, test_dev_pipeline.py, tools/dev_pipeline/README.md(79행 1항목 + 88행 직전 기준선 문장만), docs/claude/baseline-pyver-report.md. test_dev_pipeline.py는 추가만 있다(기존 줄 변경·삭제·skip 없음).
2. `previous_baseline`의 결과가 바뀌지 않았다. 같은 판 직전이 있으면 `compare_baseline`이 키 3개짜리 같은 dict를 낸다. 기존 1141행 단언이 그대로다.
3. 같은 판 직전이 없을 때만 판이 다른 조상을 쓴다. 조건은 진짜 조상, method 같음, 자기 자신 제외, 멈춤·미수락 제외, computed_utc가 가장 늦은 것이다. 이때 `prev_python` 키가 붙는다.
4. 문턱이 지금과 같다: 1~9 경고, 10 이상 `STOP_BASELINE_REGRESSED`, accept 파일만 낮춤, 문턱 상수 10. 판이 다른 비교에서도 같다. 문자열·튜플 형식과 stop일 때 notices `[]`도 그대로다. 판이 다른 후보는 python 칸이 문자열인 캐시만이다.
5. `BASELINE_PREV_OTHER_PYTHON`이 `BASELINE_NOTICE_PREFIXES`에 있다. 그래서 검사를 실패시키지 않고 결과 줄 `baseline=`에 보인다.
6. 캐시 파일 이름·`cached_baseline` 검사·옛 캐시 재비교 조건이 바뀌지 않았다. 실제 `_baseline/` 파일을 건드리지 않았다.
7. 추가 시험이 지시문 목록 8개를 덮고, 실제로 새 분기를 거친다. 새 함수를 빼면 시험 2·3·4·7이 실패하는 구조여야 한다.
8. 주문·키움·정책·상태와 무관하다. 새 외부 호출·파일 삭제가 없다.
9. 줄바꿈이 원래대로다(CRLF 파일 일괄 변환 없음).
10. 보고서에 (a)~(g)가 있고 수량·금액·표지가 없다.
11. G9: 수정안 연결표 ②③⑤의 원문 행을 대조한다. devpipe.py run_baseline_in·run_test_checks 973행·1979행, README 79행.

시험을 직접 돌려야 확인되는 항목만 이 한 줄을 쓴다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`. 파일을 고치지 않는다.
