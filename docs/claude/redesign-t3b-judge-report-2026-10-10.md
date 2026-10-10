---
id: redesign-t3b-judge-report-2026-10-10
title: 재설계 T3b 독립 Judge 판정 — 경로 길이 · 기준선 브랜치 · 기준선 동시 실행 · 큐 5분 · N1·N2·O3
date: 2026-10-10
class: 일반 변경, 파이프라인 보호 경로 → 기존 방식 독립 Judge(별도 세션, 파일 수정 없음)
judge_prompt: docs/claude/redesign-t3b-judge-prompt-2026-10-10.md
builder_prompt: docs/claude/redesign-t3b-builder-prompt-2026-10-10.md
target: .claude/worktrees/t3b (브랜치 worktree-t3b, HEAD = base 918b59d, 미커밋 — 추적 수정 7 + 새 파일 1)
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: Cowork(병합 판단·배포 4절) · 관제판 redesign-t3b
---

# PASS

- K1~K9 모두 통과다. 병합 조건은 없다. 아래 "의견"은 병합을 막지 않으며, 다음 파이프라인 보호 경로 변경 때 판단한다.
- K6 판단: `quantity_authority: false` → authority는 **그대로 둔다**(안전 쪽). 근거는 K6 칸에 있다.
- 확인 방법: Builder 보고는 증거로 쓰지 않았다.
  - 직접 확인: `git status`·`git diff 918b59d`, 바뀐 파일 원문(base는 `git archive`로 임시 폴더에 풀어 비교), worktree 테스트 직접 실행, 스키마 감사, PowerShell 파서, `register-dev-tasks.ps1 -PlanOnly`.
  - devpipe 함수 직접 호출(임시 폴더 스크립트, 저장소 읽기만): 경로 길이, `main_snapshot`(메인 index 불변 확인), `compare_main`, 시간대 판정.
  - 전체 스위트는 test-runner가 원본 바이트를 임시 폴더에 저장했다. 숫자와 실패 집합은 그 원본 stderr에서 내가 직접 셌다.
  - 실행하지 않은 것: dev-run·dev-merge·dev-queue, 모델을 부르는 `claude -p`, 작업 등록(-PlanOnly만), 키움, 비밀 파일.
  - 부수 확인: 이 세션에서 파이프라인 스크립트 이름이 들어간 Bash 명령 2건이 실제로 거절됐다(P9 deny가 걸려 있음).
- 한계: git 폴더 한도 247은 다시 재지 않았다. MS 문서 규칙(디렉터리 생성은 MAX_PATH−12)과 맞고, 더 엄격해지기만 하므로 받아들였다.

## 판정표

`devpipe` = tools/dev_pipeline/devpipe.py, `run` = tools/dev-run.ps1, `test` = manage-us-stock-strategy/tests/test_dev_pipeline.py. 줄 번호는 worktree 파일 기준이다.

| # | 판정 | 근거 |
|---|---|---|
| K1 범위 | PASS | `git diff 918b59d --name-only` = 7개: test_dev_pipeline.py, dev-queue.ps1, dev-run.ps1, README.md, devpipe.py, judge-prompt.md, register-dev-tasks.ps1. 새 파일은 docs/claude/redesign-t3b-builder-report-2026-10-10.md 1개다. 모두 2절 허용 경로 안이다. settings.json·.gitignore·dev-merge.ps1·builder-rules.md·authority-paths.txt·commit-docs.ps1·run-docs-commit.ps1·CLAUDE.md·AGENTS.md·정책·상태는 변경 0이다. 무시 파일은 복사 3개(sha256 = 메인)와 `__pycache__` 3폴더뿐이고, 내 실행 전후 같다. 바뀐 텍스트 파일은 모두 CRLF만 있고 BOM이 없다. |
| K2 D1 | PASS | 수식은 devpipe:384-404 `path_budget`이다. parent = UTF-16(`<repo>\.claude\worktrees`)+1, 이름 = max(id, `_base-<sha8>`), 꼬리 = 1 + 최장 추적 경로(파일·폴더 따로). 한도는 :81-82(파일 259 = NUL 포함 260, 폴더 247)다. 최장 경로는 base의 `ls-tree -r -z --full-tree`에서 센다(:370-381). 단위는 UTF-16이다(:365). preflight는 git 검사 뒤, CLI 검사 앞에서 잰다(:1404-1413). 실패하면 STOP_PREFLIGHT이고, run 모드면 LATEST.json에 남긴다(:1461-1465). dev-run은 preflight가 실패하면 잠금·init 전에 끝난다(run:543-548). init-run은 run.json을 쓰기 전에 실제 base로 다시 잰다(:1477-1479). 경계 테스트는 test:825(259/260), :833(247/248), :846(이 PC), :878(CLI·worktree·_baseline 전 정지), :892(init-run)이다. **직접 재계산**(메인 `E:\…\코덱스저장소`, base 918b59d2): main UTF-16 18, parent 37. 추적 파일 1304개, 최장 파일 203·폴더 119다(devpipe 값 = 독립 계산 값). 결과: 10자 → 255 통과 · 28자 → `PATH_TOO_LONG:269>259:max_id=18` · 18자 → 259 통과 · 19자 → 260 거절. |
| K3 D2 | PASS | `git worktree add -B devpipe-base-<sha8> <temp> <base>` 1곳(devpipe:1048)이다. `--detach`는 0개다(test:1342-1353이 count도 단언). `git branch -D`도 1곳(:1097)이다. 그 앞에서 다음을 모두 확인한다(:1081-1096). ① 이름이 devpipe-base-로 시작하고 = `base_branch_name(base)` ② `branch_created is True` ③ tip = base ④ 어느 worktree도 체크아웃하지 않음. 이미 있는 브랜치가 다른 커밋을 가리키면 옮기지 않고 STOP_BASELINE이다(:1040-1042, test:957). 만든 뒤 `symbolic-ref`·HEAD가 맞는지 확인한다(:1022-1029). 캐시 이름은 `<base>-py<ver>-b2.json`(:962)이다. 재사용은 method = b2일 때만이다(:989-1003, test:941). **11건 실측**: `_baseline/4395fa45…-py3.13.15.full.err`(detached, Ran 2670, failures=19 errors=20)와 이번 worktree 전체 스위트의 실패 블록을 비교했다. detached에만 있는 것은 11개다: test_save_daily_pipeline test_16~25, test_v2_4_preopen_refresh test_cli_writes_valid_report_runtime_and_manifest. 11개 모두 traceback에 `git_branch: shorter than minLength`가 있다. 브랜치 쪽에만 있는 것은 0, 공통 28이다. 브랜치 쪽 블록에는 git_branch가 0번 나온다. 스키마의 git_branch 제약은 minLength 1뿐이다. 그래서 `devpipe-base-…` 이름으로도 같은 28이 기대된다. |
| K4 D3 | PASS | 순서(run:395-488)는 다음과 같다. init → `baseline-prepare`(동기, :431-437) → PENDING이면 `Start-Baseline`(:434, :180) → snapshot-includes(:445) → main-snapshot(:453) → Builder 1(:461) → `Wait-Baseline`(:469, :188) → `Stop-Baseline`(정리, :470) → main-compare(:486) → check(:488). 정적 단언은 test:1307이다. 임시 worktree는 Builder 전에 만든다. 백그라운드 `baseline-run`은 읽기 git과 테스트만 한다(devpipe:1540, :1061-1078). 지우는 일은 Builder가 끝난 뒤 dev-run이 한다. 그래서 git 쓰기 경합이 없다. 스위트 안 git 호출도 check-ignore·ls-files·rev-parse·status 같은 읽기뿐이다. check는 `load_baseline_for_check`만 쓴다(:1138-1148, :1665). base·python·b2·ran·failures가 다르면 MISMATCH, 없으면 MISSING이고 둘 다 exit 2 → STOP이다(test:1017, :1038). run.json에 python이 있다(:1496). 정리는 모든 종료 경로에서 불린다. ① Complete-Run 첫 줄(run:367) ② Stop-RecordChanged 첫 줄(:248) ③ main finally에서 Exit-Lock 앞(:571-574) ④ Builder TIMEOUT(:462 → Complete-Run → 프로세스 트리 종료 → cleanup). 정리 대상은 dev-run의 `--repo`와 정해진 이름(`_base-<sha8>`·`devpipe-base-<sha8>`)으로 검증한다(devpipe:1125-1135, :1553-1566, test:1027). run.json 값은 쓰지 않는다. 바깥 상한 75분(run:32)은 Builder와 겹친다. 그래서 최악 합계가 T3 때(기준선 70 직렬)보다 줄어든다. dev-queue 340분 안에서 맞고, 넘으면 STOP_QUEUE_TIMEOUT(fail-closed)으로 이전과 같다. |
| K5 D4 | PASS | register-dev-tasks.ps1:34 `$queueIntervalMinutes = 5`, :35 6시간이다. dev-queue.ps1은 머리말 1줄만 바뀌었다(900초·340분 상수 그대로, test:1273 통과). **-PlanOnly 직접 실행**(exit 0, 등록 없음 — :117-119가 Register 전에 끝남): DevQueue `TRIGGER_REPETITION = interval=PT5M duration=INDEFINITE`, `EXECUTION_LIMIT_MINUTES = 360`, `MULTIPLE_INSTANCES = IGNORE_NEW`. DocsCommit은 23:30 · 15분이다. 출력과 정적 테스트(test:1291) 모두 이름이 두 개뿐이다. |
| K6 N1 | PASS (그대로 둠) | 추가 줄마다 `added_value_reasons`(devpipe:830-842)가 사유를 **더하기만** 한다(:859). class는 바뀌지 않은 `escalate`(:875)로 정하고, 내리는 코드는 없다(test:1077 — authority에서 general로 안 내려감). 테스트 test:1054는 `*_approved: true`·`{"const": true}`, `execution_quantity = 5`·`12`·`{"type": [...]}` → authority를 본다. test:1065는 false/none/null/`"none"`/`{"const":"none"}`/`$null`/비교식/표 칸 → general을 본다. **판단 11**: 저장소에서 `quantity_authority: false`는 "권한 없음" 뜻이다. 근거: 추적 47줄(43파일) — 스키마 14개 `{"const": false}`, 스크립트 6곳 `False`, 승인 정책 6개, docs/v2.6.13 "quantity_authority=false … preserved". CLAUDE.md는 이 키를 쓰지 않는다. 문서 머리말은 `none`을 쓴다. 그런데 2026-09-25 이후 추가된 quantity_authority 줄은 **모두 none 형태이고 false는 0건**이다. 또 기존 줄을 고치면 이미 REMOVED_LINE 표지로 authority가 된다. 그래서 오탐은 새 줄에 false를 쓸 때만 생기고, 예상 주간 사용자 접촉은 약 0이다. 지금 고치려면 Builder·Judge를 한 번 더 돌려야 한다(사용자 접촉 2회 이상). **판정: 안전 쪽이므로 그대로 둔다. 병합 전 수정 아님.** 다음 보호 경로 변경 때 none 값에 `false`·`$false`를 더한다(의견 1). |
| K7 O3 | PASS | **a.** `Save-Records`(run:226)는 init·prepare·snapshot·main-snapshot·기준선 끝 뒤에 돈다. `Test-Records`(:236)는 그 밖의 12단계 직전마다 돈다. 대상은 run.json·baseline.json·캐시·baseline-worktree.json·main-before.json이다(devpipe:95, :1153-1180). 어긋나면 `Stop-RecordChanged`(:247-252)가 기준선 정리 → `write-latest`만 쓴다. result.json이 없으므로 병합할 수 없다(do_merge :2033-2034). 정적 단언은 test:1328, 변조·삭제 테스트는 test:1112이다. 기준선이 도는 동안 새로 생긴 기록은 expected에 없어서 무시된다(오탐 없음). **b.** `main_snapshot`(devpipe:1199)은 `git --no-optional-locks status --porcelain -z --untracked-files=no --no-renames`(:1204)를 쓴다. docs/claude/ 밖 줄과 감시 폴더 2개의 모든 파일(추적·무시) sha256을 찍는다. `compare_main`(:1222)은 **새로 나타난** 상태 줄과 바뀐·생긴·사라진 감시 파일만 센다. 테스트: test:1147(정책·상태·무시·새 정책·추적 코드 → STOP), :1164(docs 변경·문서 커밋 → 통과). **시간대 예외**는 `skip_state`일 때 stock-strategy-system/ 경로만 뺀다(파일·상태 줄 모두). 정책과 다른 추적 줄은 남는다. 직접 호출 결과: skip=True → `([' M tools/x.ps1'], ['workspace/policies/p.json'])`. 경계는 06:09:59 아님, 06:10 맞음, 06:40 맞음, 06:40:01 아님이다(test:1173, :1185). **메인 index 직접 확인**: 실제 메인에 `main_snapshot`을 돌린 앞뒤로 `.git/index`의 mtime·크기·sha256이 같다. `*.lock`도 없다(16초, 전체 스위트와 동시). |
| K8 회귀 | PASS | **J2**: P6 보호 상수 블록이 base와 바이트로 같다. protected_violations·allowed_entry_overlaps_protected·validate_block·parse_prompt_block·inspect_tree·judge-prep·parse-judge·fix-prep·include_candidates/snapshot·refresh_include_snapshot·evaluate_tests·run_checks의 함수 본문 sha도 base와 같다. 기준 커밋 읽기와 Judge 상수도 그대로다. **J3**: `$BuilderAllowedTools`·`$BuilderDisallowedTools`(run:38-51)와 Start-Builder·Start-Judge(:332-364)는 diff 밖이다. 정적 테스트 test:1236-1271이 통과한다. **J6**: dev-merge.ps1 diff는 0이다. devpipe의 `verify_for_merge`~`cmd_write_latest` 구간이 base와 바이트로 같다. rebase 경로는 `ensure_baseline`을 그대로 부른다(:2015). 이제 브랜치 방식이다. 변화 1건: "devpipe는 브랜치를 지우지 않는다"에 지시문이 허용한 예외 1곳이 생겼다(devpipe:1097, devpipe-base-만). 옛 단언 test:1288 `'"branch", "-d'`는 대소문자를 구분해서 `-D`를 잡지 못한다. 대신 새 test:1342가 1곳과 그 조건을 단언한다. **테스트**(worktree 직접 실행): test_dev_pipeline* **Ran 118 OK**(119.8초, 86 + 32 — `def test_` 89 → 121), test_auto_core* 89 OK, test_reconcile_broker_state* 56 OK, test_portfolio_exposure_judge_fixes* 29 OK. **전체 스위트**(PYTHONUTF8·PYTHONIOENCODING·PYTHONDONTWRITEBYTECODE): `Ran 2710 tests in 365.111s` · `FAILED (failures=19, errors=9, skipped=2)` · FAIL/ERROR 줄 28개(중복 0). 집합은 K3의 공통 28과 같고, Builder 0단계 a 목록·2차 T3 Judge 28과도 같다. 새 실패 0, 사라진 것 0이다. 2678 + 32 = 2710, skipped 2 → 2다. 스키마 감사는 exit 0, `"status": "PASS"`이다. .ps1 6개는 파서 오류 0·비ASCII 0·LF = CRLF다. **픽스처 잔여물**: 실행 뒤 `git branch --list "devpipe-base-*"` 0개, 브랜치 81개 그대로다. `.claude/worktrees` 목록, `_baseline` 10개 파일, t3b 상태·무시 목록도 실행 전과 같다. |
| K9 Builder 판단 | PASS | 아래 표. |

## K9 Builder 판단 1~13

| # | 판정 | 메모 |
|---|---|---|
| 1 폴더 한도 247 추가 | 수용 | MAX_PATH−12 규칙과 맞다. 더 엄격하기만 하다(지금 폴더 171). |
| 2 preflight 위치 | 수용 | CLI 검사 앞이다. `--version/--help`는 모델 호출이 아니다. init-run에서 다시 잰다. |
| 3 이미 있는 브랜치 | 수용 | base에 있으면 쓰되 지우지 않는다. 다른 커밋이면 STOP이다. |
| 4 `branch -D` + 사전 조건 | 수용 | 확인과 삭제 사이의 틈은 자기 이름 공간 안이다. |
| 5 정리는 Builder 뒤 | 수용 | git 쓰기 경합을 없앤다. TIMEOUT이면 트리 종료다. |
| 6 표지 먼저 기록·이름 대조 | 수용 | `--repo`는 dev-run 인자이고 이름은 고정이다. |
| 7 check는 STOP(기다리지 않음) | 수용 | dev-run이 이미 기다린다. 없으면 fail-closed다. |
| 8 바깥 상한 75분 | 수용 | Builder와 겹쳐서 최악 합계가 오히려 준다. |
| 9 O3a 방식·대상 확대 | 수용 | 대상을 넓혔다. STOP 때는 write-latest만이라 병합할 수 없다. |
| 10 O3b 범위·시간대 예외 | 수용 | 정책·다른 추적 파일은 예외 밖이다. 오탐 원인은 의견 3. |
| 11 N1 값 규칙(false → authority) | 수용(그대로) | K6 판단. 의견 1. |
| 12 테스트 시간 +40~50초 | 수용 | 이번 실측 119.8초(부하 중). |
| 13 0단계 a 직접 실행 | 수용 | 실패 집합을 원본에서 따로 확인했다(K3·K8). |

## 조건

없음.

## 의견 (병합 차단 아님 — 다음 파이프라인 보호 경로 변경 때)

1. **N1 false**: `ADDED_NONE_VALUES["quantity_authority"]`에 `"false"`, `"$false"`를 더한다. 그리고 test의 `'"quantity_authority": {"const": false}'`를 general 쪽으로 옮긴다. 저장소 의미(스키마 const false = 권한 없음)와 맞추는 것이고, 안전 비용은 없다. 지금은 오탐 빈도가 약 0이라 미룬다.
2. **dev-merge와 dev-run 기준선 겹침(기존 문제, T3 1차 O6)**: 같은 base에서 두 쪽이 동시에 돌면 `_base-<sha8>` 폴더·브랜치와 캐시 파일을 함께 쓴다. 이때 한쪽이 다른 쪽 임시 worktree를 지울 수 있다. 그러면 기준선 실패 집합이 부풀어 그 base 캐시에 남을 수 있다(새 실패를 가리는 방향). T3b가 만든 문제는 아니다(기준선 시간 길이 같음). dev-merge가 살아 있는 dev-run 잠금을 보면 멈추게 하기를 권한다.
3. **O3b 오탐 원인(fail-closed)**: 실행 중 Cowork가 상태·정책을 쓰면 STOP_MAIN_TOUCHED가 된다. 실측 예: 10-10 08:52 대조 apply, 10-09 16:04 저널, 10-09 여러 번 stock-strategy-system/backtests 재현 파일, 10-10 14:23 정책 auto_core.json. stock-strategy-system 아래 `__pycache__`도 같다. 지시문 범위대로이고 새 id로 다시 큐에 넣으면 된다. 첫 몇 주 빈도를 보고 좁힐지 정한다(좁히기는 완화라서 Judge 대상이다).
4. **Windows 파일 교체 경합(드묾, fail-closed)**: 다른 프로세스가 run.json·baseline.json·캐시를 읽는 순간 `os.replace`로 덮어쓰면 실패할 수 있다(공유 삭제 없음). 그러면 STOP_INTERNAL_ERROR 또는 STOP_RUN_RECORD_CHANGED로 끝난다. 틈은 밀리초 단위다.
5. **정리 실패 표시**: `baseline-cleanup`이 LEFT(exit 1)여도 dev-run은 계속하고, result.json `baseline_cleanup`에만 남는다. DEV-RUN 한 줄이나 LATEST에 보이게 하기를 권한다. 강제 종료(340분·전원)로 남은 `devpipe-base-*` 브랜치는 그 뒤 "이번 실행이 만든 것"이 아니라서 자동으로 지워지지 않는다. `git branch --list "devpipe-base-*"` 확인을 관제판 점검에 넣기를 권한다.
6. **max_id 표시**: 필요 길이가 기준선 이름 14자 때문에 넘으면 `max_id`가 14보다 작게 나온다. 이때는 어떤 id도 통과하지 못하는데 표시는 그 점을 말하지 않는다. 표시만 문제이고 정지는 맞다.
7. **동시 실행 부하**: 이번 전체 스위트는 대상 테스트·메인 스냅샷과 동시에 돌았는데도 정확히 28이었다. 그래도 부하 때문에 기준선 쪽에서만 실패하면 그 테스트의 회귀가 가려진다. 병합 뒤 첫 작업에서 지시문 1절 ①(기준선 실패 = 28)을 확인할 때 같이 본다.

## 병합 뒤 (지시문 4절 그대로)

- 사용자: 병합 → `register-dev-tasks.ps1` 1번(5분 간격 덮어쓰기).
- Cowork: 다음 파이프라인 작업 1건에서 ① 기준선 실패 28 ② 큐 → Builder 시작 ≤ 6분 ③ log의 `BASELINE start/end`와 `BUILDER start/end` 겹침을 확인한다.
