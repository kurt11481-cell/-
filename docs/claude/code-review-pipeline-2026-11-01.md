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

## 추가: dev-run·dev-merge 스크립트 리뷰 (2026-11-02 15:4x KST, 읽기 전용)
읽은 범위: tools/dev-merge.ps1 전체(136줄), tools/dev-run.ps1 36~70행·325~360행(Builder·Judge 실행 플래그), tools/dev_pipeline/devpipe.py 1274~1300행(`main_snapshot`·`compare_main`). dev-queue.ps1·commit-docs.ps1과 dev-run.ps1의 나머지 줄은 **미검토**.

### P-4 (중, P-3과 같은 종류) Builder는 시험 파일을 통해 아무 Python이나 실행할 수 있다
- dev-run.ps1 38~45행: Builder 허용 명령은 `python -m unittest *`다. Builder는 worktree 안에서 시험 파일을 쓸 수 있다(acceptEdits). 그래서 시험 파일에 넣은 코드는 `python -m unittest discover ...`로 그대로 실행된다. 명령 문자열 허용 목록은 실행되는 코드 내용을 제한하지 못한다.
- 지금 막는 선: ① 실행 뒤 메인 checkout의 workspace/policies/·stock-strategy-system/ 모든 파일 해시와 추적 파일 상태를 실행 전과 비교한다(devpipe.py 1274~1300행, main-before.json·main-check-N.json). 바뀌면 잡힌다. 다만 막지는 못하고 **뒤에 알아챈다**. ② MCP 전부 차단(`--strict-mcp-config`, `mcp__*` deny). ③ 키움 브리지가 주문 엔드포인트를 막는다(authority-paths.txt 주석). ④ Judge가 diff를 읽는다.
- 남는 빈틈: 감시 폴더 밖의 부작용은 비교에 잡히지 않는다. 예를 들면 홈 폴더 쓰기, 예약 작업 등록, 네트워크 호출, 비밀 파일 읽기다. Builder 모델이 지시문을 따른다는 전제에 기대고 있다.
- 제안: 당장 고칠 일은 아니다. P-3과 묶어 "실행 전 내용 검사 또는 격리 실행" K3 검토 안건으로 둔다. 짧게 할 수 있는 일은 Judge 확인 항목에 "새 시험 파일이 subprocess·socket·os.system·파일 시스템 절대 경로를 쓰는지"를 더하는 것이다. judge-prompt.md도 tools/ 아래라 K3다.

### 문제 없음으로 본 것
- dev-merge.ps1: main checkout의 result.json만 믿는다. 조건은 devpipe가 모두 다시 계산한다. -ApproveAuthority는 대화형 콘솔·두 표준 핸들·Enter 한 번을 요구하고, 판단이 안 되면 멈춘다(39~85행). 스크립트 주석 스스로 "사람임을 증명하지는 못한다"고 밝힌다(41~43행). 원격 push·강제·브랜치 삭제는 없다(15행).
- Judge는 Read·Grep·Glob만 쓰고 MCP는 차단된다(dev-run.ps1 356~358행).
- auto-core decision_mode: 설정이 없으면 기본은 compare다(auto_core_decide.py 418행). 일지에 쓰기 직전에 apply·kill_switch·provenance를 다시 확인한다(770~779행).

## 추가: 3차 리뷰 — dev-queue·commit-docs (2026-11-03 21:5x KST, 읽기 전용)
읽은 범위: tools/dev-queue.ps1 전체(150줄), tools/commit-docs.ps1 전체(85줄). 기준 커밋 8f2fdd5.

### CD-1 (중) commit-docs는 docs/claude 아래면 권한 문서도 그대로 커밋한다
- commit-docs.ps1 44행의 경로 검사는 세 가지만 본다. `docs/claude/` 아래인지, `..`이 없는지, `_pending/`이 아닌지다. authority-paths 같은 별도 관문은 없다.
- 그래서 헌법(constitution-v*.md), automation-redesign-2026-10-10.md 같은 권한 문서와 파이프라인이 쓰는 docs/claude/dev-runs/·_dev-queue/ 파일도 _pending 한 줄이나 23:30 자동 커밋으로 들어갈 수 있다. 사람 검토는 없다.
- 이미 아는 사실과 맞다. constitution-location 기억에 "스레드 문서 쓰기·23:30 자동 커밋은 막지 않는다"고 적혀 있다. card-evidence-registry.json은 CLAUDE.md 51행에 따라 대화형 세션이 일부러 커밋하는 파일이라 예외가 정상이다.
- 지금 막는 선: 자동 코어가 읽는 docs/claude 입력 4곳은 커밋 검사(coreinput2)를 받는다. 다만 이 검사는 "커밋됐는가"만 보고, "누가 바꿨는가"는 보지 않는다.
- 고치는 법(안): commit-docs에 보호 목록(헌법·결정 색인 머리·dev-runs·_dev-queue)을 두고, 그 경로는 거부하거나 별도 표시를 요구한다. tools/ 변경이라 **K3**다. 급하지 않다. 23:30 커밋 기록이 git에 남아 뒤에 추적할 수 있기 때문이다.

### 문제 없음으로 본 것
- dev-queue.ps1: 잠금 파일은 pid와 시작 시각을 함께 본다(Test-LockAlive). 예약 작업은 MultipleInstances IgnoreNew다. 그래서 두 번 겹쳐 돌지 않는다. task id는 정규식 `^[a-z0-9][a-z0-9-]{1,47}$`으로 거른다. dev-run은 340분으로 제한된다.
- 알아 둘 점: 지시문이 아직 커밋되지 않았으면 dev-queue가 commit-docs를 한 번 돌린다. 이때 그 지시문만이 아니라 대기 중인 _pending 전부가 커밋된다. 결함은 아니다. 다만 대기 줄에 다른 문서가 있으면 함께 들어간다.
