---
id: baseline-pyver-report
title: "기준선 감시 — 같은 Python 판 직전이 없으면 판이 다른 조상과 비교 — Builder 보고"
date: 2026-11-16
source: "docs/claude/baseline-pyver-builder-prompt.md (수정안 id baseline-pyver-proposal-2026-11-13, 사장 결정 2026-11-16)"
base: 129eb9e7c5236eba86e9a29aa5f9b6bdd469aa29
branch: worktree-baseline-pyver
---

## 결론
같은 Python 판 직전 기준선이 없을 때만, 같은 조건(방식·조상·멈춤 제외·형식)으로 판이 다른 가장 늦은 조상 기준선과 비교한다. 문턱(1~9 경고, 10 이상 `STOP_BASELINE_REGRESSED`, accept 파일만 낮춤)은 그대로다. `test_dev_pipeline.py` 162건 OK(새 시험 10건 포함). 커밋·push·병합 없음.

## (a) 바꾼 함수·줄
- `tools/dev_pipeline/devpipe.py:94` `BASELINE_NOTICE_PREFIXES`에 `"BASELINE_PREV_OTHER_PYTHON"` 추가 → `run_test_checks`(973행 부근)가 정보로 분류, `DEV-RUN … baseline=`에 표시.
- `devpipe.py:627` `baseline_rose_verdict` — `prev_python`이 문자열이면 notices 맨 앞에 `BASELINE_PREV_OTHER_PYTHON:<판>`(0건·1~9·ACCEPTED 분기). stop 분기는 지금처럼 notices `[]`. 다른 문자열·튜플 형식 불변.
- `devpipe.py:1014` 새 도우미 `newest_ancestor_baseline(repo, base, python_ok)` — 옛 `previous_baseline` 본문을 그대로 옮기고 python 조건만 함수로 받음.
- `devpipe.py:1034` `previous_baseline(repo, base, python)` — 서명 그대로, `python_ok = (값 == python)`.
- `devpipe.py:1040` 새 `previous_baseline_other_python(repo, base, python)` — `python_ok = (문자열이고 != python)`.
- `devpipe.py:1045` `compare_baseline` — 같은 판 직전이 있으면 지금과 같은 키 3개. 없을 때만 판이 다른 조상을 찾고, 찾으면 키 3개 + `prev_python`. 못 찾으면 지금처럼 `{"prev_base": None, "added_failures": [], "removed_failures": []}`.
- `tools/dev_pipeline/README.md:79` 기준선 정보 reason 목록에 `BASELINE_PREV_OTHER_PYTHON:<직전 python>` 1항목 추가.
- `README.md:88` '직전 기준선 = …' 문장 뒤에 판이 다른 조상 대체 규칙 한 문장 추가.

## (b) 직전 기준선 고르는 규칙
1. 같은 판: python·방식이 같고, base가 다르고, SHA·failures·computed_utc 형식이 맞고, 멈추지 않았고(`baseline_stopped` 아님), 지금 base의 진짜 조상(`merge-base --is-ancestor`)인 캐시 중 computed_utc 최신 1개.
2. 1이 없을 때만: 같은 조건이되 python이 **문자열이고 지금 판과 다른** 캐시 중 최신 1개. 찾으면 결과에 `prev_python`을 남긴다.
3. 둘 다 없으면 `BASELINE_PREV_NONE`(지금과 같음).

## (c) 시험
명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"` (worktree 안, Python 3.15.2)

마지막 3줄:
```
----------------------------------------------------------------------
Ran 162 tests in 194.630s
OK
```

추가한 시험(기존 시험은 고치지·지우지·건너뛰지 않음):
- `BaselineWatchTests.test_pyver_same_python_previous_wins_over_newer_other_python` (시험 1)
- `BaselineWatchTests.test_pyver_other_python_ancestor_ten_or_more_stops_with_no_notices` (시험 2)
- `BaselineWatchTests.test_pyver_other_python_ancestor_warning_leads_with_notice` (시험 3)
- `BaselineWatchTests.test_pyver_other_python_ancestor_accepted_leads_with_notice` (시험 4)
- `BaselineWatchTests.test_pyver_cache_without_string_python_is_not_an_other_python_candidate` (시험 4-1)
- `BaselineWatchTests.test_pyver_other_python_non_ancestor_is_left_out` (시험 5)
- `BaselineWatchTests.test_pyver_stopped_other_python_ancestor_is_left_out` (시험 6, accept를 두면 다시 후보가 됨도 확인)
- `BaselineWatchTests.test_pyver_same_failures_give_only_the_other_python_notice` (시험 7)
- `BaselineWatchTests.test_pyver_notice_is_information_after_evaluate_tests` (시험 8, `BASELINE_NOTICE_PREFIXES`로 분류)
- `BaselineWatchCheckTests.test_other_python_notice_is_a_run_test_checks_notice` (시험 8 보강: `run_test_checks`에서 reasons `[]`, notices 2줄)

`test_latest_ancestor_same_python_and_method_only`의 `previous_baseline(…, "0.0.0")` is None 단언은 그대로 통과.

## (d) 옛 캐시·새 키 호환
- `cached_baseline` 유효성 검사와 `"prev_base" not in data` 재비교 조건은 바꾸지 않았다. 이미 `prev_base`가 있는 캐시(예: 판이 바뀐 뒤 `prev_base: null`로 저장된 캐시)는 다시 비교하지 않고 그대로 읽힌다.
- 새 키 `prev_python`은 `run_baseline_in`이 compare 결과를 그대로 저장할 때만 캐시에 들어간다. 키가 없는 캐시는 `baseline_rose_verdict`에서 지금과 같은 결과를 낸다.
- 후보 선택에서 `prev_python` 키는 보지 않는다. 판이 다른 캐시를 고를 때 그 캐시의 `python` 칸만 본다.

## (e) dev-merge 경로
dev-merge 재시험은 `ensure_baseline`(devpipe.py:1209) → `cached_baseline` 또는 `run_baseline_in` → `compare_baseline` 순서로 같은 함수를 쓴다(호출 devpipe.py:2115, 그 뒤 `run_test_checks`). `cmd_baseline`(1619행)도 같다. 추가 동작 변경은 필요 없었고 BLOCKED.md는 쓰지 않았다. 다른 판 알림은 `BASELINE_NOTICE_PREFIXES`에 들어 있어 dev-merge 재시험 reasons로 가지 않는다(시험 `test_other_python_notice_is_a_run_test_checks_notice`).

## (f) stop일 때 notices `[]`
`test_pyver_other_python_ancestor_ten_or_more_stops_with_no_notices`가 판이 다른 조상(실패 0) 대비 +13에서 `(("STOP_BASELINE_REGRESSED", "<sha8>:+13"), [])`를 확인했다. 다른 판 비교였다는 사실은 기준선 dict의 `prev_python`에 남는다.

## (g) 지금 `_baseline/`에 적용하면
`workspace/outputs/dev-runs/_baseline/`(읽기만)에 Python 3.15.2 캐시가 있고, 그중 e629c22·853a5db·92c8546·b2e0f08이 129eb9e의 조상임을 `git merge-base --is-ancestor`로 확인했다. 따라서 3.15.2에서 다음 기준선은 같은 판 직전을 쓰고 판이 다른 비교는 쓰이지 않을 것으로 예상한다(실제 다음 실행에서 확인 필요). 이미 저장된 캐시는 바뀌지 않는다(옛 b2e0f08 캐시의 `prev_base: null`도 그대로).

## 실행 경위 메모
지시문 2단계 명령으로 `.claude/worktrees/baseline-pyver`를 만들었으나 이 세션의 편집 훅이 자기 worktree 밖 쓰기를 막아, 손대지 않은 그 worktree와 브랜치를 지우고 지시문의 대체 경로대로 이 세션 worktree(`.claude/worktrees/goofy-tesla-d71591`)에서 `git switch -C worktree-baseline-pyver 129eb9e…`로 맞춘 뒤 작업했다.

표지 없음.
