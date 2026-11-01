---
id: baseline-watch-proposal-2026-11-01
title: "개발 큐 기준선 실패 수 감시 규칙 — K3 수정안 (P-1 ②)"
date: 2026-11-01
status: "제안 — 사장 승인 전. 코드·설정·예약 변경 없음"
source: "사장 결정 카드 '기준선 감시 규칙 먼저'(사장실 회사PC 스레드 '전체 코드 리뷰 진행', 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX95ajUhDbX3j93JEr3vYnrgM, 2026-11-01 23:24 KST, 계정=사장). 근거 docs/claude/code-review-pipeline-2026-11-01.md P-1"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 한 줄 결론
기준선(병합 전 기준 커밋의 전체 시험)을 새로 잴 때마다, 직전 기준선과 실패 목록을 비교한다. 실패가 늘면 경고하고, 크게 늘면 개발 큐를 멈춘다. 10/30처럼 실패가 22+9에서 276+10으로 조용히 늘어나는 일을 그날 바로 잡는다.

## 왜 필요한가
- 지금 devpipe는 "이번 작업이 기준선보다 새로 깨뜨린 시험"만 본다(tools/dev_pipeline/devpipe.py 623~670행 `evaluate_tests`). 기준선 실패 수가 늘어도 아무 검사를 하지 않는다.
- 10/30에는 git 밖 실제 상태 파일 때문에 기준선 실패가 255건 늘었다. 이틀 동안 아무도 몰랐고, 그동안 그 시험들은 회귀를 잡지 못했다.
- 23:22 KST 병합(00f5fd9, state-fixture2)으로 원인 하나는 없앴다. 다음 기준선은 실패 20·오류 9 수준으로 줄 것이다(state-fixture2 checks-2.json). 그러니 감시를 걸기에 지금이 가장 좋다.
- 기준선이 늘어나는 다른 길도 남아 있다. ① 개발 큐를 거치지 않은 직접 코드 커밋(10월에 40건, P-2) ② 다른 git 밖 파일 의존(FileNotFoundError 6건, P-1) ③ 날짜 경과.

## 바꿀 내용 (안)
1. **직전 기준선 찾기.** `run_baseline_in`(devpipe.py 1062행)에서 새 기준선을 계산한 직후에 한다. `_baseline/` 캐시 가운데 같은 python·method(b2)이고 기준 커밋이 지금 기준 커밋의 조상(`git merge-base --is-ancestor`)인 것만 고른다. 그중 `computed_utc`가 가장 늦은 1개를 쓴다. 자기 자신은 뺀다.
2. **비교.** `added = 지금 실패 − 직전 실패`, `removed = 직전 실패 − 지금 실패`를 구한다. 둘 다 이름 목록으로 기준선 json에 적는다(`prev_base`, `added_failures`, `removed_failures`).
3. **판정** (아래 B안 추천):
   - A안(경고만): `added`가 1건 이상이면 reasons에 `BASELINE_FAILURES_ROSE:<직전 sha8>:+N`을 붙인다. 판정(READY_TO_MERGE 등)은 그대로다.
   - **B안(경고 + 큰 증가는 멈춤, 추천):** 1~9건이면 A안과 같이 경고만 한다. 10건 이상이면 `STOP_BASELINE_REGRESSED`로 멈추고, 늘어난 실패 이름을 `baseline-regressed.txt`에 적는다. 10/30 사례(+255)는 멈추고, 가끔 흔들리는 시험 1~2건으로는 큐가 서지 않는다.
   - C안(엄격): 1건만 늘어도 멈춘다. 가장 안전하지만, 직접 커밋 하나가 시험을 깨면 고칠 때까지 모든 개발 큐가 선다.
4. **직전 기준선이 없을 때**(캐시 삭제·첫 실행): `BASELINE_PREV_NONE`을 정보로 남기고 그대로 진행한다.
5. **보이는 곳.** 결과 줄(`DEV-RUN … baseline_rose=+N`)과 docs/claude/dev-runs/<id>.md에 1줄을 넣는다. 사장실 스레드는 결과를 읽을 때 이 줄을 보고한다.
6. **바꾸지 않는 것.** 새 실패 판정, ran 감소·skip 증가 검사, 권한 경로(authority-paths.txt), dev-merge의 ff·rebase 규칙.

## 시험 (manage-us-stock-strategy/tests/test_dev_pipeline.py에 추가)
- 실패 목록이 같으면 경고 없음.
- +1이면 경고만, 판정 불변.
- +10이면 STOP_BASELINE_REGRESSED, 목록 파일 생성(B안).
- 조상이 아닌 캐시는 더 늦게 만들어졌어도 비교 대상에서 빠짐.
- 직전 기준선이 없으면 BASELINE_PREV_NONE, 진행.
- 실패가 줄기만 하면 경고 없음(removed만 기록).

## 경로와 승인
- tools/는 보호 경로라 개발 큐 작업이 고칠 수 없다(authority-paths.txt 8~9행). 그래서 **K3 수동 경로**로 간다. 사장 승인 → 회사PC에서 Builder worktree와 별도 읽기 전용 Judge → 병합은 사장 결정 뒤(CLAUDE.md "Authority/limit change"). 선례로 devpipe 변경 T3·T3b·T3c(23b878b·cd6a56d·8218154)가 있다.
- 이 스레드는 dev-run·병합을 실행하지 않는다. 승인되면 Builder·Judge 지시문을 쓰고, 실행은 회사PC 실행 스레드에 맡긴다.
- 되돌리기: 커밋 1개를 revert한다. 캐시 json에 더한 키는 옛 코드가 읽지 않으므로 그대로 둬도 된다(확인 필요: `cached_baseline` 1000행 검사가 모르는 키를 거부하지 않는지 Builder가 확인).

## 위험·한계
- 기준 커밋이 바뀔 때마다 이미 기준선을 새로 잰다(약 11분). 추가 비용은 git 호출 몇 번뿐이다.
- 같은 날 두 작업이 서로 다른 조상 기준선을 쓰면 비교 대상이 다를 수 있다. 조상 조건으로 줄이지만 완전히 없애지는 못한다.
- 늘어난 실패를 기준선에 "받아들이는" 절차는 없다. B안에서 10건 이상 멈췄을 때는 원인을 고치거나, 사장 결정으로 그 기준선을 승인하는 작은 표식 파일(`_baseline/accept-<sha8>.txt`)을 두는 방법을 이번 변경에 같이 넣는다(안). 표식 파일은 사장실 스레드가 아니라 사장이 직접 만든다.
- P-2(작업 브랜치에서 safety-ci 미실행)는 이번 범위가 아니다.
