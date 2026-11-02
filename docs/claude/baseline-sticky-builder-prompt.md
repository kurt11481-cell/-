---
id: baseline-sticky-builder-prompt
title: "기준선 감시 멈춤이 다음 기준선에서 풀리지 않게 — baseline-sticky Builder"
date: 2026-11-02
class: "K3 수동 경로(tools/ 보호 경로). 회사PC worktree Builder(Opus) → 별도 읽기 전용 Judge → 병합은 사장 결정 뒤 사장 PowerShell"
source: "docs/claude/baseline-sticky-proposal-2026-11-02.md, 사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9C8VBvQ1bH4eg6EfpQkp8So '승인, 오늘 진행' 2026-11-02 09:02 KST"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 목표
`previous_baseline`(tools/dev_pipeline/devpipe.py 1004~1019행 부근)이 **멈춘 기준선**을 비교 대상에서 건너뛰게 한다. 멈춘 기준선 = 자기 `added_failures` 길이가 `BASELINE_ROSE_STOP` 이상이고, 그 기준 커밋의 accept 표식(`baseline_accept_path` 999행, `_baseline/accept-<sha8>.txt`)이 없는 캐시.
그러면 X에서 멈춘 뒤 문서 커밋으로 기준이 Y로 옮겨져도, Y는 X 이전의 마지막 깨끗한 기준선과 비교해 다시 멈춘다.

## 바꿀 파일 (이 4개만)
- tools/dev_pipeline/devpipe.py
- manage-us-stock-strategy/tests/test_dev_pipeline.py
- tools/dev_pipeline/README.md (기준선 감시 설명에 1~3줄)
- docs/claude/baseline-sticky-report.md (보고)

## 구현 요구
1. 후보 필터에 위 "멈춘 기준선" 제외 조건을 더한다. 정렬·조상 조건·python·method 조건은 그대로 둔다.
2. `added_failures` 키가 없는 옛 캐시는 지금처럼 후보로 둔다. 재귀 계산을 하지 않는다.
3. accept 표식이 있는 멈춘 기준선은 후보로 둔다. 표식은 코드가 만들지 않는다.
4. 문턱값, 경고·멈춤 이름, 표식 이름·위치, `evaluate_tests` 판정, dev-merge 경로, 그 밖의 판정은 바꾸지 않는다. 기존 단언을 약화·삭제·skip 하지 않는다.
5. 캐시 json에 이미 `added_failures`가 저장되는지 확인한다(baseline-watch 병합 cb5c5d4). 저장되지 않는 경로가 있으면 BLOCKED.md에 적고 멈춘다.

## 시험 (test_dev_pipeline.py에 추가)
- X 멈춤(+10, 표식 없음) → 자손 Y는 X 이전 W와 비교해 STOP_BASELINE_REGRESSED.
- X 멈춤 + accept-X → Y는 X와 비교, 경고·멈춤 없음.
- X 멈춤 뒤 Y에서 실패를 W 수준으로 고침 → 멈춤 없음.
- 비교 키 없는 옛 캐시 → 후보로 남음.
- 1~9건 경고 기준선 → 후보로 남음.
기존 baseline-watch 시험의 임시 저장소 도우미를 쓴다. 실행 명령은 이 한 줄만, 글자 그대로: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`. 전체 스위트는 돌리지 않는다. git은 status·diff·log만. `python -c` 같은 다른 셸 작업은 하지 않는다.

## 지켜야 할 것
- 위 4개 파일 밖은 손대지 않는다. tools/dev-run.ps1·dev-merge.ps1·authority-paths.txt·builder-rules.md·judge-prompt.md·.claude/·정책·상태 금지.
- 고치는 파일의 줄바꿈(CRLF)을 지킨다. 일괄 변환 금지.
- 주문·키움·정책·상태·일지·원장·예약과 무관. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음.
- 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/baseline-sticky-report.md
(a) 바꾼 함수·줄(파일:행) (b) 제외 조건 요약 (c) 시험 결과 마지막 3줄과 추가한 시험 이름 (d) 옛 캐시 호환 확인 (e) 지금 `_baseline/`에 멈춘 기준선이 있는지(파일 이름만, Read·Glob으로 확인; 확인 못 하면 "확인 필요"). 수량·금액·주문 표지 문자열을 적지 않는다("표지 없음").
