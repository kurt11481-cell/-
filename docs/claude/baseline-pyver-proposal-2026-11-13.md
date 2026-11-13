---
id: baseline-pyver-proposal-2026-11-13
title: "기준선 감시가 Python 판이 바뀌어도 꺼지지 않게 — K3 수정안 (코드 리뷰 2차 H-2)"
date: 2026-11-13
status: "제안 — 실행 당일 수정안 id를 단 사장 카드 전. 코드·설정·예약 변경 없음"
source: "docs/claude/code-review-2026-11-13.md 1절 H-2·2절 #2, 사장 결정 카드 '급한 2건 + 실행기 점검 착수'(cmsg_0137MRzn9nuDvvQmVxm6WeX9PCF1dsnNAnGfBH91YwoK3p, 2026-11-13 14:40:53 KST — 착수 방향만, 6절)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 한 줄 결론
직전 기준선을 같은 Python 판에서 못 찾으면, 판이 다른 가장 가까운 조상 기준선과 비교한다. 지금과 같은 문턱(1~9건 경고, 10건 이상 `STOP_BASELINE_REGRESSED`, accept 파일로만 낮춤)을 그대로 적용한다. 11/11처럼 Python 판이 바뀌면서 실패가 0 → 168건으로 뛰는 일을 그날 멈춤으로 잡는다.

## 왜 필요한가
- `tools/dev_pipeline/devpipe.py` 1011~1028행 `previous_baseline()`은 python이 같은 캐시만 고른다.
  - 같은 판이 없으면 1033~1035행 `compare_baseline`이 `prev_base: None`을 낸다.
  - 그러면 630~633행 `baseline_rose_verdict`가 `BASELINE_PREV_NONE`(정보, 94행 BASELINE_NOTICE_PREFIXES)만 남긴다.
- 실제 사례:
  - `_baseline/03721d5f…-py3.13.15-b2.json`(11/07): 실패 0.
  - `_baseline/b2e0f08d…-py3.15.2-b2.json`(11/11): 실패 168(pandas 164·numpy 2·tzdata 1·pypdf 1).
  - first-collect(11/11)는 `BASELINE_PREV_NONE`만 남기고 병합됐다. 그 뒤 qqq-b-core2(11/13, e629c22 기준선 168건)도 같은 판끼리 비교라 '늘어남 0'이다.
- 기준선에 들어간 실패는 `evaluate_tests`(644행)가 "새 실패"로 세지 않는다. 그동안 대시보드 시험 163건과 모듈 4개가 회귀를 못 잡았다.
- 11/13 14:46 KST 사장 터미널에서 pandas 등을 설치했다. 다음 기준선부터는 같은 판(3.15.2)끼리 비교하므로, 이번 수정의 효과는 **다음 판 변경 때**(3.15.x 패치 포함 — 캐시 키가 `py<major.minor.micro>`) 나타난다.

## 바꿀 내용 (안)
1. **새 함수** `previous_baseline_other_python(repo, base, python)`
   - 조건은 `previous_baseline`과 같다: method b2, base 다름, 진짜 조상(`merge-base --is-ancestor`), failures·computed_utc 형식, 멈췄는데 accept가 없는 캐시는 뺌(`baseline_stopped`).
   - 다만 python이 **다른** 캐시만 본다. 그중 computed_utc가 가장 늦은 1개를 고른다.
   - `previous_baseline`은 바꾸지 않는다. 같은 판 우선 규칙과, 기존 시험 `test_dev_pipeline.py` 1141행 `previous_baseline(…, "0.0.0")`이 None이라는 단언이 그대로 남는다.
2. **비교** `compare_baseline`(1031~1037행)
   - 같은 판 직전이 있으면 지금과 똑같은 dict를 낸다.
   - 없을 때만 1의 함수로 찾는다. 찾으면 같은 세 키에 `"prev_python": <그 캐시의 python>`을 더한다. 못 찾으면 지금처럼 `prev_base: None`이다.
3. **판정** `baseline_rose_verdict`(627~641행)
   - 기준선에 `prev_python`이 있으면 notices 맨 앞에 `BASELINE_PREV_OTHER_PYTHON:<prev_python>`을 둔다.
   - 그 뒤 문턱은 지금과 같다: 1~9 경고, 10 이상 STOP, accept면 ACCEPTED. 멈춤 튜플의 형식(`"<prev sha8>:+N"`)과 멈출 때 notices `[]`(641행)도 그대로 둔다(다른 판 비교였다는 사실은 캐시 `prev_python`·보고에 남음).
4. `BASELINE_NOTICE_PREFIXES`(94행)에 `"BASELINE_PREV_OTHER_PYTHON"`을 더한다. 정보 줄이라 검사를 실패시키지 않는다.
5. `tools/dev_pipeline/README.md` 79행 기준선 정보 reason 목록에 1항목을 더하고, 88행 '직전 기준선 = 캐시 중 python·방식이 같고…' 문장을 새 규칙(같은 판 우선 → 판이 다른 조상)에 맞게 고친다.

## 바꾸지 않는 것
- 문턱 `BASELINE_ROSE_STOP = 10`, accept 파일 규칙(사장이 직접 만듦, 기준 sha8 한정)
- 캐시 파일 이름(`<base>-py<ver>-b2.json`), `cached_baseline`의 유효성 검사, `previous_baseline`
- `evaluate_tests`의 새 실패·ran·skip 판정, 권한 경로, merge_mode, dev-run.ps1·dev-merge.ps1
- 옛 캐시(`prev_base`가 이미 있는 것)는 다시 비교하지 않는다(1071~1072행 그대로).

## 효과 예시(두 캐시 파일 값으로 소급 계산)
- 11/11 b2e0f08d(py3.15.2)는 같은 판 직전이 없었다. 새 규칙이면 03721d5f(py3.13.15, 실패 0)와 비교해 +168 → `STOP_BASELINE_REGRESSED`이다.
- 그날 first-collect 대신 기준선 멈춤이 보였을 것이다. 사장 선택은 둘이다: 패키지 설치 뒤 새 커밋(기준 이동)에서 새 id로 다시 돌리거나(같은 기준·같은 판이면 캐시와 저장된 비교 키를 다시 써서 또 멈춤 — devpipe.py 1059~1075행), accept 파일로 그 기준을 받아들인다.

## 위험·한계
- 판이 바뀌면 정당한 차이(판별 skip 등)로 10건 이상 늘 수 있다. 그때는 멈춘다. 원인을 보고 설치하거나 accept 파일로 받아들인다(의도한 동작).
- 판이 다른 직전 기준선이 오래됐으면, 그 사이 커밋의 회귀도 함께 늘어남으로 잡힌다(안전 쪽).
- 이미 계산된 캐시 가운데 `prev_base: None`인 것은 다시 비교하지 않는다. 다음 기준 커밋부터 적용된다.
- '같은 판 우선'이라, 더 오래된 같은 판 기준선이 더 새 다른 판 기준선보다 먼저 뽑힌다. 실패 168건이 든 e629c22(3.15.2)는 앞으로 3.15.2 기준선의 비교점으로 남는다. 11/13 설치가 충분치 않으면 그 가림이 이어진다(다음 기준선 실패 수로 확인 필요).

## 경로와 승인
- tools/는 보호 경로라 개발 큐가 고칠 수 없다(devpipe.py 109~117행 PROTECTED_PREFIXES) → **K3 수동 경로**. 선례는 baseline-watch(docs/claude/baseline-watch-proposal-2026-11-01.md, 11/02 병합)다.
- 실행 당일 이 수정안 id(`baseline-pyver-proposal-2026-11-13`)를 단 사장 결정 카드를 받는다. 받은 날 Builder를 못 띄우면 시작 직전에 다시 받는다.
- 실행 방법은 둘 중 하나다.
  - 사장실 최상위 메시지로 실행 스레드를 연다.
  - 이 스레드가 RC로 Builder(Opus, worktree `.claude/worktrees/baseline-pyver`)를 띄우고, Builder RC를 끝낸 뒤 별도 읽기 전용 Judge RC를 띄운다.
- 병합은 Judge `VERDICT: PASS` 뒤 사장 결정 카드 → 사장 PowerShell 병합 스크립트 한 줄이다(선례 baseline-watch-merge-2026-11-02.ps1).
- **순서:** 개발 큐 run(qqq-b-core2 → bar-isolate → runner-deps)과 병합이 겹치지 않게 한다. 둘 다 docs/claude 밖을 바꾸므로, 나중에 병합되는 쪽은 STOP_BASE_MOVED가 난다. 개발 큐가 비어 있고 그 run이 병합된 사이에 이 Builder를 시작한다. CLAUDE.md 119행 '권한·한도 변경 동시 1건'에 따라 qqq-b-core2(승인 종목 변경) 병합 뒤에 한다.
- 되돌리기: 커밋 1개 revert. 캐시 json의 `prev_python` 키는 옛 코드가 읽지 않는다(1068~1069행 검사는 base·python·method·ran만 봄).
- 지시문: docs/claude/baseline-pyver-builder-prompt.md, docs/claude/baseline-pyver-judge-prompt.md

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 기준선 캐시 `prev_python` 키 + 정보 줄 `BASELINE_PREV_OTHER_PYTHON:<판>`·판이 다른 비교의 `STOP_BASELINE_REGRESSED` | 개발 큐 InvestmentV2-DevQueue(5분마다) → dev-run.ps1 → devpipe.py `run_baseline_in`(1146~1151행)·`compare_baseline`(이번 변경) | devpipe.py `run_test_checks` 973행(notices)·1979행 `DEV-RUN … baseline=` 결과 줄 → `_queue/<날짜>.log`·docs/claude/dev-runs/<id>.md(README 79행) | 판이 바뀌어 실패가 10건 이상 늘면 개발 큐 run이 멈춤 → Cowork가 원인 확인 → 사장 설치 한 줄 또는 accept 파일 | 멈춤은 결과 줄·dev-runs 문서에 바로 보임. 이 비교가 다시 꺼지는 회귀는 새 시험(Judge 확인 항목 2~4)이 잡음 | 연결 |
