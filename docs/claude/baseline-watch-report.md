---
id: baseline-watch-report
title: "개발 큐 기준선 실패 수 감시 규칙(B안) — Builder 보고"
date: 2026-11-02
class: "K3 수동 경로 Builder 보고. Judge 전, 커밋·병합 없음"
source: "docs/claude/baseline-watch-builder-prompt.md, docs/claude/baseline-watch-proposal-2026-11-01.md"
---

## 결론
B안을 구현했다. 기준 커밋 d7b8b99 위 worktree `.claude/worktrees/baseline-watch`, 시험 143건 통과. BLOCKED 없음. 판단이 필요한 한계가 2.1에 있다(멈춘 기준선이 다음 기준선의 비교 대상이 됨).

## (a) 바꾼 함수·줄
tools/dev_pipeline/devpipe.py
- 상수 91~94행: `BASELINE_ROSE_STOP = 10`, `BASELINE_REGRESSED_TXT`, `BASELINE_NOTICE_PREFIXES`
- `baseline_rose_verdict` 627행(새 함수, 순수): 기준선 dict의 키만 보고 멈춤·정보 reason을 정한다
- `evaluate_tests` 644행: 끝에서 위 함수를 부른다(680행). 앞쪽의 기존 판정과 조기 반환은 그대로
- `run_test_checks` 964행: 정보 reason을 `notices`로 분리(973행), 멈춤이면 실행 폴더에 `baseline-regressed.txt` 작성
- `baseline_accept_path` 999행, `previous_baseline` 1004행, `compare_baseline` 1022행(새 함수)
- `cached_baseline` 1050행: 키가 없으면 읽을 때 비교, accept 파일은 매번 확인
- `run_baseline_in` 1125행: 비교 키를 캐시에 쓴다. accept 값은 캐시에 쓰지 않는다
- `cmd_write_result` 1915행: `notices`를 사유 목록과 DEV-RUN 줄 끝 ` baseline=…`에 붙인다(1951행)

tools/dev_pipeline/README.md: 판정 표에 STOP_BASELINE_REGRESSED 1행, 정보 reason 1줄, 기준선 항목에 직전 기준선 규칙 추가.

### 지시문 해석 2건
1. 경고를 `reasons`에 그대로 두면 판정이 바뀐다. `run_checks`는 reasons가 있으면 RETRYABLE로 보고, `rebase_and_retest`도 reasons가 있으면 멈춘다. 그래서 `evaluate_tests`는 지시문대로 reasons에 넣어 돌려주되(반환 형식 불변), `run_test_checks`가 `notices`로 분리한다. 결과 쪽 사유·DEV-RUN 줄에는 기존 출력 길로 나간다.
2. 수정안의 `baseline_rose=+N` 대신 ` baseline=<reason>`을 쓴다. 지시문의 reason 문자열을 그대로 보이게 하기 위해서다. 정보 reason이 없으면 줄은 예전과 같다.

## (b) 직전 기준선 고르는 규칙
`_baseline/` 바로 아래 `*.json`(하위 `_invalid-*`·`_quarantine-*` 폴더 제외)에서 python·method가 같고, base가 유효한 sha이며 지금 base와 다르고, failures 목록과 computed_utc가 있는 것만 후보로 둔다. computed_utc 내림차순으로 보며 `git merge-base --is-ancestor`가 참인 첫 1개를 쓴다. 조상이 아니면 더 늦어도 빠진다. git 호출 실패도 조상 아님으로 친다.

## (c) 시험 결과
명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"` (지시문의 한 줄만 실행, 전체 스위트 미실행)

```
Ran 143 tests in 134.935s

OK
```

첫 실행에서 새 시험 1건이 인자 형식 오류로 실패했고(시험 코드 쪽 문제), 고친 뒤 위 결과가 나왔다. 기존 시험 126건의 단언은 바꾸지 않았다.

추가한 시험 17건
- BaselineWatchTests: test_same_failures_add_no_reason, test_one_more_failure_warns_without_stop, test_nine_more_failures_still_only_warn, test_ten_more_failures_stop, test_accept_file_of_this_base_lowers_the_stop, test_accept_file_of_another_base_does_not_apply, test_non_ancestor_cache_is_left_out_even_when_newer, test_latest_ancestor_same_python_and_method_only, test_no_previous_baseline_is_information_only, test_fewer_failures_record_removed_only, test_old_cache_is_compared_on_read_and_stays_unchanged, test_new_cache_keeps_keys_and_accept_is_read_every_time, test_keyless_baseline_dict_adds_nothing
- BaselineWatchCheckTests: test_warning_keeps_status_and_shows_in_line_and_summary, test_notice_is_not_a_merge_retest_reason, test_stop_writes_the_list_and_reaches_the_summary, test_accepted_stop_keeps_status_ok

## (d) 옛 캐시 호환
- `cached_baseline`의 검사는 base·python·method·ran만 본다. 모르는 키를 거부하지 않으므로 새 캐시를 옛 코드가 읽어도 되고, 옛 캐시를 새 코드가 읽어도 된다.
- 키 없는 옛 캐시는 읽을 때 메모리에서만 비교한다. 파일은 다시 쓰지 않으므로 O3 기록(캐시 sha256) 대조가 깨지지 않는다(test_old_cache_is_compared_on_read_and_stays_unchanged).
- 실행 중이던 옛 `baseline.json`처럼 `prev_base` 키가 없는 dict는 새 reason을 내지 않는다.

## (e) dev-merge 경로 영향
코드 변경 없음, BLOCKED 사유 아님. `ensure_baseline`이 `cached_baseline`·`run_baseline_in`을 쓰고 `rebase_and_retest`가 `run_test_checks`를 쓰므로, **base가 움직여 rebase하는 병합에도 같은 판정이 걸린다.**
- 1~9건 경고: 병합을 막지 않는다. `merge-tests.json`의 notices에만 남고 DEV-MERGE 줄에는 나오지 않는다.
- 10건 이상: `STOP_BASE_MOVED reason=tests_after_rebase:STOP_BASELINE_REGRESSED`로 되돌리고 멈춘다. 이름 목록은 실행 폴더 `baseline-regressed.txt`. 이 동작은 새로 생긴 것이다.
- accept 파일이 있으면 경고로 낮아진다.
- ff 병합은 기준선을 재지 않으므로 이 판정을 받지 않는다.

## (f) 지금 `_baseline/`에 적용한 예상
읽기 전용으로 잰 값(2026-11-02, 새 함수 `previous_baseline`을 실제 캐시에 실행):
- 지금 base d7b8b99의 캐시 없음 → 다음 실행에서 새로 잰다
- 직전 기준선 = 751549f3 (computed_utc 2026-11-01T13:04:19Z, ran 3473, 실패·오류 합 283건)
- accept 파일 없음
- state-fixture2 병합으로 실패가 줄었으므로 **경고 없음이 예상**이다. 단 판정은 합계가 아니라 이름 차이로 하므로, 283건에 없던 이름이 다음 기준선에 나오면 그 수만큼 경고가 난다. 실제 결과는 확인 필요(다음 기준선을 재기 전에는 알 수 없음).

## 2. 한계
1. **멈춤이 다음 base에서 풀린다(Judge·사장 확인 권장).** 지시문 규칙대로면 멈춘 기준선도 캐시에 남아 다음 비교 대상이 된다. A(22건) → B(277건, 멈춤) → C(docs 커밋, 277건)이면 C는 B와 비교해 +0이고 경고 없이 진행된다. 매일 23:30 docs 커밋으로 base가 움직이므로 멈춤은 사실상 그 base 동안만 유지된다. 알아차리는 효과는 있지만 수리될 때까지 막는 장치는 아니다. 고치려면 "멈춘 기준선은 accept 없이는 비교 대상에서 뺀다" 같은 규칙이 필요한데, 지시문 범위 밖이라 넣지 않았다.
2. 멈춤은 Builder와 전체 시험이 끝난 뒤 check에서 나온다. 그 실행의 Builder 비용은 쓰인다. 지시문이 판정 위치를 `evaluate_tests`로 정했다.
3. accept 파일은 기준선을 읽을 때 본다. 멈춘 뒤 만들었으면 새 id로 돌려야 적용된다.
4. 지시문 사본은 worktree에 없었다(저장소 루트에 미추적). 루트 파일을 읽기만 했다.

수량·금액·주문 표지: 표지 없음.
