---
id: baseline-pyver-builder-prompt
title: "기준선 감시 — 같은 Python 판 직전이 없으면 판이 다른 조상 기준선과 비교 — baseline-pyver Builder"
date: 2026-11-13
class: "K3 수동 경로(tools/ 보호 경로). 회사PC worktree Builder(Opus) → 별도 읽기 전용 Judge → 병합은 사장 결정 뒤 사장 PowerShell"
source: "docs/claude/baseline-pyver-proposal-2026-11-13.md(수정안 id baseline-pyver-proposal-2026-11-13), 승인 = 실행 당일 그 수정안 id를 단 사장 결정 카드(수정안 '사장 결정 기록' 절)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 목표
기준선 감시(baseline-watch)는 같은 Python 판의 직전 기준선만 비교한다. 그래서 판이 바뀌면 `BASELINE_PREV_NONE`만 남고 꺼진다. 같은 판 직전이 없을 때 판이 다른 가장 가까운 조상 기준선과 비교하게 하고, 문턱(1~9 경고, 10 이상 `STOP_BASELINE_REGRESSED`, accept 파일만 낮춤)은 그대로 적용한다.

## 바꿀 파일 (이 4개만)
- tools/dev_pipeline/devpipe.py
- manage-us-stock-strategy/tests/test_dev_pipeline.py (시험 추가만)
- tools/dev_pipeline/README.md (79행 기준선 정보 reason 목록에 1항목 + 88행 '직전 기준선 = …' 문장만 새 규칙에 맞게)
- docs/claude/baseline-pyver-report.md (보고)

## 구현 요구
1. 새 함수 `previous_baseline_other_python(repo, base, python)`를 만든다.
   - `previous_baseline`(1011~1028행)과 같은 조건으로 고른다: method, base 다름, failures·computed_utc 형식, SHA 형식, `baseline_stopped` 제외, `merge-base --is-ancestor`.
   - 단 `isinstance(data.get("python"), str) and data["python"] != python`인 캐시만 본다. 그중 computed_utc가 가장 늦은 조상 1개, 없으면 None.
   - 같은 코드를 두 번 쓰지 말고, 공통 부분을 작은 도우미로 나눠도 된다. 그래도 `previous_baseline`의 서명·결과는 지금과 같아야 한다.
2. `compare_baseline`(1031~1037행)
   - 같은 판 직전이 있으면 지금과 **똑같은** dict를 낸다(키 3개).
   - 없을 때만 1을 부른다. 찾으면 키 3개 + `"prev_python": <그 캐시의 python 문자열>`을 낸다. 못 찾으면 지금처럼 `{"prev_base": None, "added_failures": [], "removed_failures": []}`이다.
3. `baseline_rose_verdict`(627~641행)
   - `prev_python`이 있고 prev_base가 있으면, 반환 notices 맨 앞에 `BASELINE_PREV_OTHER_PYTHON:<prev_python>`을 둔다.
   - 나머지 분기(0건 → notices만, 1~9 → ROSE 경고, 10 이상 → stop 또는 ACCEPTED)와 그 문자열·튜플 형식은 바꾸지 않는다.
   - **stop일 때는 지금처럼 notices `[]`를 돌려준다**(641행 형식 불변). 다른 판 비교였다는 사실은 캐시의 `prev_python`과 보고에만 남는다. ACCEPTED·1~9 경고일 때는 `BASELINE_PREV_OTHER_PYTHON`이 맨 앞에 붙는다.
4. `BASELINE_NOTICE_PREFIXES`(94행)에 `"BASELINE_PREV_OTHER_PYTHON"`을 더한다. 그래야 `run_test_checks`(973행)가 정보로 다루고 `DEV-RUN … baseline=`(1979행)에 보인다.
5. 새 키는 캐시에 쓰인다(`run_baseline_in` 1149~1150행이 compare 결과를 그대로 저장). 다음은 바꾸지 않는다.
   - `cached_baseline`(1057~1075행 부근) 유효성 검사.
   - 옛 캐시 재비교 조건(`"prev_base" not in data`, 1071행).
6. dev-merge 경로(`ensure_baseline`)도 같은 compare를 쓰는지 확인해 보고에 적는다. 동작을 더 바꿀 필요가 있으면 BLOCKED.md에 이유를 쓰고 멈춘다.
7. 기존 판정(새 실패, ran 감소, skip 증가, 권한 경로, merge_mode)과 기존 단언은 바꾸지 않는다. 기존 시험을 고치거나 약화·삭제·skip 하지 않는다. 특히 1141행 `previous_baseline(…, "0.0.0")` is None은 그대로 통과해야 한다.

## 시험 (test_dev_pipeline.py에 추가 — 기존 BaselineWatch 계열 클래스의 임시 저장소·`cache()` 도우미를 쓴다, 1060~1080행)
1. 같은 판 직전이 있으면 판이 다른 더 늦은 조상 캐시가 있어도 같은 판을 쓴다. 결과에 `prev_python` 키가 없다.
2. 같은 판 직전이 없고 판이 다른 조상(실패 0)이 있으면, 지금 실패 13 → `prev_base` = 그 조상, `prev_python` = 그 판, stop `STOP_BASELINE_REGRESSED`, notices `[]`.
3. 2와 같지만 +3 → stop 없음, notices = [`BASELINE_PREV_OTHER_PYTHON:<판>`, `BASELINE_FAILURES_ROSE:<sha8>:+3`].
4. 2와 같지만 이 기준 sha8의 accept 파일이 있음 → stop 없음, notices = [`BASELINE_PREV_OTHER_PYTHON:<판>`, `BASELINE_FAILURES_ROSE_ACCEPTED:<기준 sha8>:+13`].
4-1. python 칸이 없거나 문자열이 아닌 캐시는 판이 다른 후보에서 빠진다.
5. 판이 다른 캐시가 조상이 아니면 빠진다 → `BASELINE_PREV_NONE`.
6. 판이 다른 조상 캐시가 멈췄고(added ≥ 10) accept가 없으면 빠진다(`baseline_stopped`).
7. 0건 증가(같은 실패) → notices = [`BASELINE_PREV_OTHER_PYTHON:<판>`]만, stop 없음.
8. `evaluate_tests`를 거친 결과에서 `BASELINE_PREV_OTHER_PYTHON`이 `run_test_checks`의 정보 줄로 분류된다(`BASELINE_NOTICE_PREFIXES`로 확인).

실행 명령은 이 한 줄만, 글자 그대로 쓴다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`. 전체 스위트는 돌리지 않는다(.claude/hooks pyc 문제). git은 status·diff·log만 쓴다.

## 지켜야 할 것
- 위 4개 파일 밖은 손대지 않는다. 다음은 금지다: tools/dev-run.ps1·dev-queue.ps1·dev-merge.ps1·commit-docs.ps1·authority-paths.txt·builder-rules.md·judge-prompt.md·.claude/·정책·상태·`workspace/outputs/dev-runs/_baseline/` 실제 캐시 파일.
- 고치는 파일 3개(devpipe.py·test_dev_pipeline.py·README.md — git i/lf, 작업 트리 CRLF)의 줄바꿈을 지킨다. 일괄 변환 금지. 보고에 `git diff --ignore-cr-at-eol --stat`을 적는다.
- 주문·키움·정책·상태·일지·원장·예약과 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음.
- 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/baseline-pyver-report.md
- (a) 바꾼 함수·줄(파일:행)
- (b) 직전 기준선 고르는 규칙 요약(같은 판 우선 → 판이 다른 조상)
- (c) 시험 결과 마지막 3줄과 추가한 시험 이름
- (d) 옛 캐시·새 키 호환 확인
- (e) dev-merge 경로 영향
- (f) stop일 때 notices `[]` 유지를 시험으로 확인한 결과
- (g) 지금 `_baseline/`에 적용하면 다음 기준선 판정 예상: 같은 판 3.15.2 직전 e629c22가 있으므로 판이 다른 비교는 쓰이지 않음 예상(확인 필요)

수량·금액·주문 표지 문자열을 적지 않는다("표지 없음").
