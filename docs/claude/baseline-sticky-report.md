---
id: baseline-sticky-report
title: "기준선 감시 멈춤이 다음 기준선에서 풀리지 않게 — Builder 보고"
date: 2026-11-02
class: "K3 수동 경로 Builder. Judge 전, 커밋 없음"
source: "docs/claude/baseline-sticky-builder-prompt.md, docs/claude/baseline-sticky-proposal-2026-11-02.md"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 한 줄 결론
`previous_baseline`이 멈춘 기준선을 비교 대상에서 건너뛴다. 시험 150건 통과. BLOCKED 없음. 기준 커밋 8615efb, 브랜치 worktree-baseline-sticky.

## (a) 바꾼 함수·줄
- tools/dev_pipeline/devpipe.py:1004 `baseline_stopped` 새 함수
- tools/dev_pipeline/devpipe.py:1011 `previous_baseline` 설명문 수정, 1023행 후보 조건 1줄 추가
- tools/dev_pipeline/README.md:88 직전 기준선 설명 뒤에 제외 규칙 추가
- manage-us-stock-strategy/tests/test_dev_pipeline.py:1189 `BaselineWatchTests`에 도우미 2개(`after_rise`, `judged`)와 시험 7건 추가. 기존 시험은 그대로.
- 정렬, 조상·python·method 조건, 문턱값, 경고·멈춤 이름, 표식 이름·위치, `evaluate_tests`, dev-merge 경로는 바꾸지 않았다.

## (b) 제외 조건 요약
다음 둘이 모두 참이면 후보에서 뺀다.
1. 캐시의 `added_failures`가 목록이고 길이가 `BASELINE_ROSE_STOP` 이상이다.
2. 그 캐시 base의 accept 표식(`baseline_accept_path`)이 없다.

저장된 키만 읽고 재귀 계산은 하지 않는다. 표식은 읽기만 하고 만들지 않는다. 캐시를 쓰는 곳은 `run_baseline_in` 한 곳이고(devpipe.py 1149~1150행), 비교 키를 넣은 뒤 저장하므로 지시문 구현 요구 5에 걸리는 경로는 없다.

## (c) 시험 결과
명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`

```
Ran 150 tests in 169.838s

OK
```

추가한 시험 7건(지시문 5건 + 보강 2건):
- test_stop_stays_on_the_next_baseline — X 멈춤, 표식 없음 → Y는 W와 비교해 STOP
- test_stop_stays_along_a_chain_of_baselines — (보강) X·Y 모두 멈춤 → Z도 W와 비교해 STOP
- test_accepted_stop_is_the_next_comparison_point — accept-X → Y는 X와 비교, 경고·멈춤 없음
- test_accept_of_the_next_baseline_alone_does_not_clear_the_skipped_one — (보강) accept-Y만 있으면 Y는 W와 비교, 멈춤은 ACCEPTED 안내로 낮아짐
- test_fixing_the_failures_clears_the_stop — Y에서 W 수준으로 고침 → 멈춤 없음
- test_keyless_old_cache_stays_a_candidate — 비교 키 없는 옛 캐시는 후보, 재귀 계산 없음, 파일 그대로
- test_warning_baseline_stays_a_candidate — 1~9건 경고 기준선은 후보

## (d) 옛 캐시 호환
`added_failures` 키가 없는 캐시는 `baseline_stopped`가 거짓을 돌려 지금처럼 후보로 남는다. test_keyless_old_cache_stays_a_candidate가 실패 50건짜리 키 없는 캐시로 확인했다.

## (e) 지금 `_baseline/`의 멈춘 기준선
없음. 메인 체크아웃 workspace/outputs/dev-runs/_baseline/ 기준이다(Grep·Glob, 2026-11-02 KST).
- `added_failures` 키가 있는 캐시 0개. 같은 방식으로 `computed_utc` 검색은 찾히므로 검색 실패가 아니다. 비교 키가 아직 어떤 캐시에도 저장되지 않았다.
- accept 표식 0개.

## 알아둘 동작
- 캐시에 저장된 비교 결과는 다시 계산하지 않는다. 그래서 Y 캐시가 이미 있는 뒤에 accept-X를 두면 Y 자체의 멈춤은 그대로이고, 다음 기준 커밋부터 X가 비교점이 되어 풀린다. Y를 바로 풀려면 accept-Y를 둔다. 수정안 3항과 어긋나지 않는다.
- 멈춤이 이어지는 동안 reason의 비교 대상 sha8은 X가 아니라 W로 나온다.

표지 없음.
