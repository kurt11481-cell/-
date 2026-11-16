---
id: baseline-pyver-judge-report
title: "baseline-pyver 독립 Judge 판정 (읽기 전용)"
date: 2026-11-16
class: "K3 수동 경로 Judge. Builder와 다른 세션"
source: "docs/claude/baseline-pyver-judge-prompt.md, docs/claude/baseline-pyver-builder-prompt.md, docs/claude/baseline-pyver-proposal-2026-11-13.md(본 저장소 최신본 sha256 ad73970f12e988024b8934b04dd42752318e6a6bfa224fc073c90e5551b1e356)"
target: "E:\\사업\\##금동한\\코덱스저장소\\.claude\\worktrees\\goofy-tesla-d71591 · 브랜치 worktree-baseline-pyver · HEAD 129eb9e7c5236eba86e9a29aa5f9b6bdd469aa29 · 커밋 안 된 변경"
---

## 결론
허용 파일 4개만 바뀌었고, 같은 판 우선 규칙·문턱·stop 형식·캐시 규칙이 그대로이며, 판이 다른 조상 비교와 정보 줄이 지시대로 들어갔다. 시험 162건 OK를 이 세션에서 직접 다시 확인했다. 11개 항목 모두 PASS.

## 검토한 바이트 (이 세션이 Get-FileHash로 직접 계산)

| 파일 | 기대 SHA256 | 계산 SHA256 | 바이트 | 줄바꿈 | 결과 |
|---|---|---|---|---|---|
| tools/dev_pipeline/devpipe.py | 0dfeec1cc81c6a6fdd693d932f23a6555ed2680e2968b86fab9d176e54e12bf8 | 0dfeec1cc81c6a6fdd693d932f23a6555ed2680e2968b86fab9d176e54e12bf8 | 108243 | CRLF 2293/2293 | 일치 |
| manage-us-stock-strategy/tests/test_dev_pipeline.py | e6c872672c31e6b371c0afd65c78a0652b10b57c66433a3808db3e40db1dc40f | e6c872672c31e6b371c0afd65c78a0652b10b57c66433a3808db3e40db1dc40f | 120570 | CRLF 2032/2032 | 일치 |
| tools/dev_pipeline/README.md | 959e6739fea5e385594385b34041af634bac4149cbf5567fc1ffe6558774238a | 959e6739fea5e385594385b34041af634bac4149cbf5567fc1ffe6558774238a | 13896 | CRLF 94/94 | 일치 |
| docs/claude/baseline-pyver-report.md | da6b7bb47e027701e42b52ecaf99dd872cd709c804508f0fe0105b8c32628e1c | da6b7bb47e027701e42b52ecaf99dd872cd709c804508f0fe0105b8c32628e1c | 6637 | LF(새 파일) | 일치 |

시험 실행 뒤 다시 계산한 devpipe.py·test_dev_pipeline.py 해시도 같았다(시험이 대상 파일을 바꾸지 않음).

## 항목별 판정

| # | 항목 | 결과 | 근거(파일:행) |
|---|---|---|---|
| 1 | diff가 허용 파일 4개뿐, 시험 파일은 추가만 | PASS | `git status --porcelain --untracked-files=all` = M devpipe.py · M test_dev_pipeline.py · M README.md · ?? docs/claude/baseline-pyver-report.md. `git diff --numstat 129eb9e`: test_dev_pipeline.py 108 추가 / 0 삭제(test_dev_pipeline.py:1257~1352, 1400~1409 추가 블록만). README.md 2/2 = 79행·88행만. BLOCKED.md 없음. |
| 2 | `previous_baseline` 결과 불변, 같은 판이면 키 3개 dict, 1141행 단언 그대로 | PASS | devpipe.py:1034~1037 서명 같음, 조건 `value == python`은 옛 `data.get("python") == python`과 같음. 나머지 조건·정렬·조상 검사는 devpipe.py:1014~1031로 글자 그대로 옮김(옛 1011~1028). devpipe.py:1048~1059 같은 판 직전이면 `extra` 빈 dict → 키 3개. test_dev_pipeline.py:1141 단언 무변경(기준 커밋 같은 행). 시험 1(test_dev_pipeline.py:1273~1282)이 `prev_python` 없음 확인. |
| 3 | 같은 판 없을 때만 판이 다른 조상, 조건 동일, `prev_python` 키 | PASS | devpipe.py:1050~1054(같은 판 None일 때만 호출), devpipe.py:1040~1042(`isinstance(value, str) and value != python`), 공통 조건 devpipe.py:1023~1030(method·base 다름·SHA·failures·computed_utc·`baseline_stopped` 제외·`merge-base --is-ancestor`·computed_utc 최신). |
| 4 | 문턱·형식 불변, 판이 다른 비교도 같음, stop일 때 notices `[]`, 후보는 python 문자열만 | PASS | devpipe.py:91 `BASELINE_ROSE_STOP = 10` 무변경. devpipe.py:638~644 분기·문자열 같음, `lead`만 앞에 붙음(634~636), stop은 `[]`(644 = 옛 641). accept는 devpipe.py:642 `baseline_accepted`만. 시험 2·3·4·4-1(test_dev_pipeline.py:1284~1309). |
| 5 | `BASELINE_PREV_OTHER_PYTHON`이 `BASELINE_NOTICE_PREFIXES`에 있음 → 정보·`baseline=` 표시 | PASS | devpipe.py:94. `run_test_checks` devpipe.py:976·986~987(reasons에서 빠지고 notices로), 결과 줄 devpipe.py:2000~2001. 시험 test_dev_pipeline.py:1341~1352·1400~1409. |
| 6 | 캐시 이름·`cached_baseline`·옛 캐시 재비교 불변, 실제 `_baseline/` 무접촉 | PASS | devpipe.py:994~995, 1081~1097(옛 1059~1075) diff 없음, `"prev_base" not in data` devpipe.py:1093(옛 1071). 본 저장소 `workspace/outputs/dev-runs/_baseline/` 최신 수정 시각 2026-11-16 15:13(853a5db…, 승인 16:34 KST 이전). Builder worktree에는 `_baseline/` 폴더 없음. 시험은 임시 저장소만 씀(test_dev_pipeline.py:1058~1061, 1067~1071). |
| 7 | 추가 시험이 8개 목록을 덮고 새 분기를 거침, 새 함수 없으면 2·3·4·7 실패 | PASS | 1→1273, 2→1284, 3→1290, 4→1295, 4-1→1302, 5→1312, 6→1323, 7→1335, 8→1341(+1400 보강). 2·3·4·7은 같은 판 캐시가 없고 판이 다른 캐시만 있는 구성이라, 새 함수가 없으면 `prev_base` None → `BASELINE_PREV_NONE`이 되어 단언이 실패하는 구조. |
| 8 | 주문·키움·정책·상태와 무관, 새 외부 호출·파일 삭제 없음 | PASS | diff 안의 호출은 기존 `read_json`·`git merge-base --is-ancestor`(devpipe.py:1029)뿐이고 새 명령·삭제·쓰기 경로 없음. 정책·상태·키움 관련 줄 없음. |
| 9 | 줄바꿈 원래대로 | PASS | `git ls-files --eol`: 세 파일 i/lf w/crlf. 작업 트리 CRLF 수 = LF 수(위 표). `git diff --numstat`(143+/13−)과 `--ignore-cr-at-eol --stat`(143+/13−) 같음 → 일괄 변환 없음. |
| 10 | 보고서에 (a)~(g), 수량·금액·표지 없음 | PASS | baseline-pyver-report.md:13(a)·23(b)·28(c)·52(d)·57(e)·60(f)·63(g). 69행 "표지 없음". 수량·금액 문자열 없음. |
| 11 | G9: 연결표 ②③⑤ 원문 행 대조 | PASS | 기준 커밋 129eb9e 원문에서 확인: `run_baseline_in` 1146~1151행(1149 compare 결과 저장·1150 캐시 쓰기, 수정 뒤 1168~1173), `run_test_checks` notices 973행(수정 뒤 976), `DEV-RUN … baseline=` 1979행(수정 뒤 2001), README 79행 정보 reason 목록(이번에 항목 추가). 행 번호 이동은 이번 diff(+22줄)에 따른 것이고 내용은 같음. ⑤ "끊김은 새 시험 2~4가 잡음" = 위 7번 구조로 확인. |

## 시험 (이 세션이 직접 실행)
- 명령(Builder worktree 안, 글자 그대로): `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`
- Python 3.15.2, exit 0, 마지막 줄: `Ran 162 tests in 187.798s` / `OK`

## 관찰 (판정에 영향 없음)
- 수정안 28·40행은 "`previous_baseline`은 바꾸지 않는다"고 적었으나, Builder 지시문 구현 요구 1은 서명·결과를 지키는 도우미 분리를 허용한다. 서명·조건·결과가 같음을 2번에서 확인했다.
- 판이 다른 비교로 멈췄을 때 결과 줄에는 다른 판이라는 표시가 없다(notices `[]`, 지시대로). 그 사실은 캐시 `prev_python`과 보고에만 남는다.

VERDICT: PASS
