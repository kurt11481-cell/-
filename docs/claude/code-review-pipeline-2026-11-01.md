# 코드 리뷰 ③ 개발 파이프라인·안전 장치 (2026-11-01)

status: 읽기 전용 리뷰 결과 — 코드·설정·예약 변경 없음. 테스트는 실행하지 않음(기존 기록만 읽음).
작성: 사장실 회사PC 스레드 "전체 코드 리뷰 진행"

## 읽은 범위
- tools/dev_pipeline/devpipe.py 623~670행(테스트 판정), .claude/hooks/kiwoom_order_block.py 전체(147줄), .github/workflows/safety-ci.yml
- workspace/outputs/dev-runs/_baseline/*.full.err (10/27~10/30 기준선 8개)
- dev-run.ps1(579줄)·dev-merge.ps1·dev-queue.ps1: **미검토**

## 발견

### P-1 (상) 기준선 실패가 늘어도 아무 경보가 없어서 회귀가 가려짐
- devpipe.py 625·636·642행: 새 실패 = 이번 실패 − 기준선 실패. 기준선 실패 수 자체는 검사하지 않는다. 검사하는 것은 ran·skipped·expected 수뿐이다(643~655행).
- 기준선 전체 테스트 기록:

| 기준선 커밋 | 날짜 | 실행 | 실패 | 오류 |
|---|---|---|---|---|
| 1e43b43 | 10/29 | 3416 | 22 | 9 |
| 33bae7d | 10/30 | 3423 | 276 | 10 |
| a1ce322 | 10/30 | 3423 | 276 | 10 |

- 새로 생긴 실패는 255건이고, 없어진 실패는 0건이다. 모두 test_portfolio_decision_dashboard(Manual timing·corporate action 계열 240건 이상)와 test_evaluate_timing_integration 7건이다. 대부분 `AssertionError: False is not true`이고, validate_manual_direction_evidence가 False를 돌려준 경우다.
- 그 사이 바뀐 코드는 auto_core_reconcile.py와 그 테스트뿐이다(`git diff --stat 1e43b43 33bae7d`, docs/claude 제외). 시험 대상 코드가 그대로인데 결과가 바뀌었으므로, **시험이 저장소 밖 조건에 의존한다**고 본다. 시간 경과일 수도 있고, 설치 사본(~/.codex/skills 등)이나 workspace 같은 git 밖 파일일 수도 있다. 정확한 원인은 **확인 필요**.
- 같은 기록에 기준선 worktree에서 workspace/outputs/... 파일을 찾지 못한 FileNotFoundError가 6건 있다(git 밖 파일 의존의 직접 증거). 이 6건이 10/29 이전부터 있던 실패인지는 확인하지 않았다.
- 영향: 이 286건의 시험(대시보드·수동 분석 경로)에서 진짜 회귀가 생겨도 지금 파이프라인은 통과시킨다.
- 수정 후보: ① devpipe에 "기준선 실패 수가 직전 기준선보다 N건 넘게 늘면 STOP" 규칙을 둔다(개발 파이프라인 = 권한·보호 경로라 **K3**). ② 원인 진단을 하나의 작업으로 둔다. 테스트를 실행해야 하므로 사장 터미널이나 개발 큐에서 한다.

### P-2 (중) GitHub safety-ci가 작업 브랜치에서 돌지 않음
- safety-ci.yml 3~6행: on pull_request, push main. 작업 브랜치 push(23:30 자동 커밋 포함)로는 돌지 않는다.
- 10월 코드 커밋 가운데 개발 큐 병합은 33건이고, 직접 커밋은 40건이다(`git log --first-parent --no-merges`, docs/claude 제외). 직접 커밋에는 auto-core·reconcile 수정이 들어 있다. 직접 커밋을 할 때 전체 테스트를 돌렸는지는 **확인 필요**.
- 수정 후보: 트리거에 작업 브랜치를 추가한다. 단 Windows 러너 사용량이 들고, 현재 기준선 실패 286건 때문에 매번 빨간불이 된다. 그래서 P-1을 정리한 뒤에 하는 것이 맞다.

### P-3 (중, 알려진 한계) 주문 차단 hook은 "파일을 쓴 뒤 실행"하는 경로를 막지 못함
- kiwoom_order_block.py 9~10행: 파일 쓰기 도구는 대상이 아니다(문서에 표식을 인용할 수 있게 하려는 의도). 그래서 표식을 담은 스크립트 파일을 쓰고 `python x.py`로 실행하면 명령 문자열에는 표식이 없어 통과한다.
- 또 이 hook은 회사PC의 Claude Code 세션에만 걸린다. 사장실 원격 스레드의 device_bash에도 적용되는지는 **확인 필요**(기존 메모와 같은 결론). 이번 리뷰의 device_bash 호출도 hook 밖에서 돌았을 가능성이 높다.
- 지금 다른 방어선: CLAUDE.md 금지 규칙, 키움 주문 도구 금지, order_authority=false. 키움 MCP 쪽 주문 기능 차단 여부는 kiwoom_commands 확인 전이라 **확인 필요**.
- 제안: 코드 수정보다 먼저, 이 한계를 안전 문서에 1줄로 명시한다. 막을 방법(예: 실행 직전 스크립트 내용 검사)은 **K3** 검토 안건으로 둔다.

### 문제 없음으로 본 것
- hook은 입력을 읽지 못하거나 오류가 나면 거부한다(fail closed, 133~143행). 따옴표·이스케이프로 표식을 숨긴 경우도 잡는다(32~38행).
- 파이프라인은 테스트 수 감소·skip 증가·schema 실패를 STOP 사유로 본다.

## 결론을 바꿀 조건
P-1 원인이 "2026-10-30이 지나면서 기한이 끝난 고정 시험 데이터"로 확인되고 코드 회귀가 0건이면, P-1은 (중)으로 낮춘다. 그래도 기준선 감시 규칙은 필요하다.

## 추가: P-1 원인 진단 결과 (2026-11-01 15:43 KST, 개발 큐 p1-baseline-diag2)
- 출처: .claude/worktrees/p1-baseline-diag2/docs/claude/p1-baseline-diag2-report.md. Judge 판정은 FAIL이고, 그래서 병합하지 않았다. Judge 2차(workspace/outputs/dev-runs/p1-baseline-diag2/judge-2.json)는 **주 결론과 243건의 추적이 원문과 맞다**고 확인했다. FAIL 사유는 그 밖 5~6건의 세부 원인 설명이 틀렸다는 것이다. 보고서에는 보유 수량이 들어 있어서 docs/claude로 옮기지 않는다.
- 결론: 원인은 **EXTERNAL_FILE**이다. 시험이 git 밖의 **실제 상태 파일** `stock-strategy-system/portfolio_state.json`을 읽는다(tests/test_evaluate_timing_integration.py:101-102, test_portfolio_decision_dashboard.py:2336-2337). 파이프라인은 기준선과 Builder worktree를 만들 때마다 메인의 실제 상태 파일을 복사한다(.worktreeinclude:1-2, devpipe.py:1049-1055).
- 계기: 10/30 07:45 KST 판정 때 상태 파일이 rev31로 갱신되면서 보유 종목에 신원 등록부 범위 밖의 종목이 들어왔다(s7-hold-gap-2026-10-30.md:15-17, materialize_instrument_identity_artifact.py:36-39). 그 뒤 신원 NOT_VERIFIED → validate_manual_direction_evidence False로 이어져 243건이 실패한다.
- TIME(날짜 경과)과 CODE(코드 회귀)는 근거가 없다.
- 뜻: **테스트 결과가 계좌 보유에 따라 달라진다.** 보유가 바뀔 때마다 기준선이 조용히 바뀌고, 그 시험들이 회귀를 못 잡는다.
- 수정 후보: ① 두 시험 파일이 저장소 안 고정 fixture 상태를 읽게 바꾼다(테스트만 변경). ② P-1의 기준선 실패 수 감시 규칙(K3).
