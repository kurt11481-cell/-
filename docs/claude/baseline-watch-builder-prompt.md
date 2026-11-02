---
id: baseline-watch-builder-prompt
title: "개발 큐 기준선 실패 수 감시 규칙(B안) — baseline-watch Builder"
date: 2026-11-01
class: "K3 수동 경로(tools/ 보호 경로). 회사PC worktree Builder(Opus) → 별도 읽기 전용 Judge → 병합은 사장 결정 뒤 사장 PowerShell"
source: "docs/claude/baseline-watch-proposal-2026-11-01.md, 사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX96N42R8EVfpkqMD55ex6miT 'B안: 경고, 10건 이상 멈춤' 2026-11-01 23:30 KST"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 목표
devpipe가 기준선(기준 커밋의 전체 시험)을 쓸 때마다, 직전 기준선과 실패 목록을 비교한다.
- 늘어난 실패가 1~9건이면 경고 reason `BASELINE_FAILURES_ROSE:<직전 sha8>:+N`만 붙이고 판정은 그대로 둔다.
- 10건 이상이면 `STOP_BASELINE_REGRESSED`로 멈추고, 늘어난 실패 이름을 실행 폴더 `baseline-regressed.txt`에 한 줄씩 적는다.
- 사장이 직접 만든 `workspace/outputs/dev-runs/_baseline/accept-<기준 sha8>.txt`가 있으면, 그 기준 커밋에 한해 멈춤을 경고로 낮춘다(reason `BASELINE_FAILURES_ROSE_ACCEPTED:<sha8>:+N`). 이 파일을 코드가 만들지 않는다.
- 직전 기준선이 없으면 reason `BASELINE_PREV_NONE`(정보)만 남기고 진행한다.

## 바꿀 파일 (이 4개만)
- tools/dev_pipeline/devpipe.py
- manage-us-stock-strategy/tests/test_dev_pipeline.py
- tools/dev_pipeline/README.md (판정 표·reason 목록에 새 항목 1~3줄)
- docs/claude/baseline-watch-report.md (보고)

## 구현 요구
1. 직전 기준선: `_baseline/` 캐시 json 가운데 python·method(`BASELINE_METHOD`)가 같고, base가 지금 base와 다르며, `git merge-base --is-ancestor <그 base> <지금 base>`가 참인 것. 그중 `computed_utc`가 가장 늦은 1개. 조상이 아니면 더 늦게 만들어졌어도 뺀다.
2. 비교 결과(`prev_base`, `added_failures`, `removed_failures`)를 기준선 dict에 넣는다. 새로 계산할 때(`run_baseline_in`)는 캐시 json에도 쓴다. 캐시에서 읽은 기준선에 이 키가 없으면(옛 캐시) 그때 계산한다. 즉 **캐시를 다시 쓰는 실행에서도 판정이 매번 적용**되어야 한다.
3. 판정은 `evaluate_tests`(순수 함수)에서 기준선 dict의 키만 보고 한다. 멈춤은 기존 stop 튜플 형식(`("STOP_BASELINE_REGRESSED", "<prev sha8>:+N")`)으로 돌려준다. 문턱값은 상수 `BASELINE_ROSE_STOP = 10`.
4. 결과 줄과 docs/claude/dev-runs/<id>.md에 경고·멈춤이 보이게 한다. 이미 reasons·stop이 그곳에 나가는 길이 있으면 그 길을 쓴다. 새 출력 경로를 만들지 않는다.
5. `cached_baseline`(990행 부근)의 유효성 검사가 새 키 때문에 옛·새 캐시를 거부하지 않는지 확인한다.
6. dev-merge 경로(`ensure_baseline`, 1113행)도 같은 판정을 받는지 확인하고, 받는다면 보고에 적는다. 동작을 바꿀 필요가 있으면 BLOCKED.md에 이유를 적고 멈춘다(이번 범위는 dev-run 판정).
7. 기존 판정(새 실패, ran 감소, skip 증가, 권한 경로, merge_mode)은 바꾸지 않는다. 기존 단언을 약화·삭제·skip 하지 않는다.

## 시험 (test_dev_pipeline.py에 추가)
- 실패 목록이 같으면 새 reason 없음.
- +1 → `BASELINE_FAILURES_ROSE` 경고, stop 없음.
- +10 → `STOP_BASELINE_REGRESSED`.
- +10이지만 accept 파일 있음 → 경고(ACCEPTED), stop 없음.
- 조상이 아닌 캐시는 더 늦어도 비교에서 빠짐(임시 git 저장소, 기존 시험의 임시 저장소 도우미가 있으면 그것을 쓴다).
- 직전 없음 → `BASELINE_PREV_NONE`.
- 줄기만 함 → 경고 없음, removed만 기록.
- 키 없는 옛 캐시 → 읽을 때 계산되어 판정 적용.
실행 명령은 이 한 줄만, 글자 그대로: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`. 전체 스위트는 돌리지 않는다(.claude/hooks pyc 문제). git은 status·diff·log만.

## 지켜야 할 것
- 위 4개 파일 밖은 손대지 않는다. tools/dev-run.ps1·dev-merge.ps1·authority-paths.txt·builder-rules.md·judge-prompt.md·.claude/·정책·상태는 금지.
- 고치는 파일의 줄바꿈(CRLF)을 지킨다. 일괄 변환 금지.
- 주문·키움·정책·상태·일지·원장·예약과 무관. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음.
- 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/baseline-watch-report.md
(a) 바꾼 함수·줄(파일:행) (b) 직전 기준선 고르는 규칙 요약 (c) 시험 결과 마지막 3줄과 추가한 시험 이름 (d) 옛 캐시 호환 확인 결과 (e) dev-merge 경로에 미치는 영향 (f) 지금 `_baseline/`에 이 규칙을 적용하면 다음 기준선에서 나올 판정 예상(실패가 줄어든 상태라 경고 없음 예상 — 확인 필요). 수량·금액·주문 표지 문자열을 적지 않는다("표지 없음").
