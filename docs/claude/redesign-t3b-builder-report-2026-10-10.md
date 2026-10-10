---
id: redesign-t3b-builder-report-2026-10-10
title: 재설계 T3b Builder 보고 — 경로 길이 preflight · 기준선 브랜치 · 기준선 동시 실행 · 큐 5분 · N1·N2·O3
date: 2026-10-10
status: Builder 완료(병합 전, Judge 대기)
prompt: docs/claude/redesign-t3b-builder-prompt-2026-10-10.md (0~3절)
worktree: .claude/worktrees/t3b (브랜치 worktree-t3b, base 918b59d2)
authority: order_authority=false · quantity_authority=none · execution_quantity=null (개발 절차만)
consumers: T3b Judge(지시문 6절 K1~K8) · Cowork(병합 명령·배포 4절) · 관제판 redesign-t3b
---

# 재설계 T3b Builder 보고

커밋·병합·push·작업 등록은 하지 않았다. 모델을 부르는 `claude -p`, dev-run·dev-merge·dev-queue 실행도 하지 않았다.

## 1. 0단계 (읽기만)

### a. 이 worktree(clean) 전체 스위트 기준선
- 명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"` (편집 전, 브랜치 worktree-t3b, 18:12:02→18:17:25 KST, exit 1).
- 원본 출력에서 직접 셈: **Ran 2678 · `FAILED (failures=19, errors=9, skipped=2)` · `FAIL:`/`ERROR:` 줄 28개(중복 없음)**.
  subTest 4건(`test_unapproved_provider_symbols_fail_closed` ticker=BRK.B·BRKb·COST·ZZZZ)은 id가 각각 다르다.
- 실패 id 28개:
  - ERROR: setUpClass (test_holding_baseline_observation_audit.HoldingBaselineObservationAuditTests) · setUpClass (test_mvll_canonical_volume_lineage.MvllCanonicalVolumeLineageTests) · setUpClass (test_provider_limitation_audit.ProviderLimitationAuditTests)
  - ERROR: test_materialize_kiwoom_session_aware_acceptance_candidate …test_05_materialized_candidate_passes_binding_validator · test_nbis_v4_kiwoom_price_authority …test_live_price_artifact_schema_and_semantics · …test_valuation_uses_kiwoom_and_no_double_count · test_portfolio_decision_order_intent …test_lmt_candidate_classification_is_verified_but_non_actionable · test_nbis_v3_shadow_activation …test_price_evidence_preserves_same_session_kiwoom_conflict · test_validate_research_packet …test_snapshot_fixture_declares_contract_version
  - FAIL: test_materialize_kiwoom_session_aware_acceptance_candidate …test_12_allowed_drift_is_recorded_and_validates · test_instrument_identity_authority …test_15_current_fixed_activation_is_exactly_bound · test_materialize_instrument_identity_artifact …test_candidate_support_does_not_replace_active_registry · test_evaluate_timing_integration …test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch · test_portfolio_decision_dashboard …test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan
  - FAIL: test_v2_6_7_session_aware_kiwoom_priority — test_bom_raw_sha_mismatch_rejected · test_crlf_raw_sha_mismatch_rejected · test_duplicate_provider_scope_fails_closed · test_extended_provider_scope_candidate_validates_without_activation · test_guarded_priority_requires_locked_acceptance_manifest · test_historical_and_inactive_candidate_are_not_current_acceptance · test_malformed_provider_scope_fails_closed · test_missing_acceptance_hash_blocks_guarded_transition · test_scope_04_checked_in_provider_scopes_are_complete_and_locked · test_scope_acceptance_hash_mismatch_blocks_guarded_transition · test_unapproved_provider_symbols_fail_closed ×4(subTest)
- 브랜치 조건 대조(K3 근거, 기록만 읽음): t3-trial-1 1회차의 detached 기준선 `workspace/outputs/dev-runs/_baseline/4395fa45…-py3.13.15.json` = Ran 2670 · 실패 39 · skipped 2.
  이 28개와 비교하면 **detached에만 있는 것 11개, 브랜치에만 있는 것 0개**: test_save_daily_pipeline test_16~test_25(10개) + test_v2_4_preopen_refresh test_cli_writes_valid_report_runtime_and_manifest(1개).
  같은 기준선 full.err에 `git_branch` 줄 11개. 나머지 28개는 id가 같다. 즉 D2 뒤 기준선 실패 = 28(브랜치 조건 값)이 기대값이다.

### b. 경로 길이
- 추적 파일 1304개. 최장 파일 경로 **203**(UTF-16 = 문자 수, ASCII): `workspace/research/provider-evidence/kiwoom/2026-08-28/fdbda8e4…/session-aware-priority-acceptance-pgr-jpm-cme-v-inactive-superseding-candidate.json`(2026-08-29 것도 203). 최장 폴더 경로 **119**.
- 메인 체크아웃 `E:\사업\##금동한\코덱스저장소` = UTF-16 **18**(UTF-8로는 40바이트). `<메인>\.claude\worktrees\` = 37.
- 따라서 필요 길이 = 37 + max(id, 14) + 1 + 203 = 241 + max(id, 14). 14 = 기준선 임시 이름 `_base-<sha8>`. 허용 최대 id = **18**. 1회차 id(28자) = 269 > 259.

### c. 문서 근거
- `git worktree add -B` — git-worktree.adoc:195-202 (git 2.56.0.windows.1 설치본 `C:\Program Files\Git\ucrt64\share\doc\git-doc\`): "With `add`, create a new branch named <new-branch> starting at <commit-ish>, and check out <new-branch> into the new worktree … By default, `-b` refuses to create a new branch if it already exists. `-B` overrides this safeguard, resetting <new-branch> to <commit-ish>." `--detach`는 :205-207.
- `git branch -D` — git-branch.adoc:101-108 "`-d` … The branch must be fully merged …", "`-D` Shortcut for `--delete --force`." :122-126 "In combination with `-d` … allow deleting the branch irrespective of its merged status". :221 checked out in any worktree인 브랜치는 대상에서 빠진다(실제로 git은 다른 worktree가 체크아웃한 브랜치의 삭제를 거절한다 — 코드도 따로 확인).
- `core.longpaths` — git-config.html:4108-4114 "Enable long path (> 260) support for builtin commands in Git for Windows. This is disabled by default". 이 PC 값: 설정 없음(기본 false).
- MAX_PATH — Microsoft Learn "Maximum Path Length Limitation": "the maximum length for a path is MAX_PATH, which is defined as 260 characters … and a terminating null character. For example, the maximum path on drive D is "D:\some 256-character path string<NUL>"", "When using an API to create a directory … the directory name cannot exceed MAX_PATH minus 12". 길이 단위는 WCHAR(UTF-16).
- **이 PC 실측**(scratchpad 임시 저장소, `git -c core.longpaths=false worktree add`):
  ```
  FILE file=259 parent_dir=235 rc=0
  FILE file=260 parent_dir=236 rc=128 fatal: Could not reset index file to revision 'HEAD'.
  DIR parent_dir=247 file=249 rc=0
  DIR parent_dir=248 file=250 rc=128 fatal: cannot create directory at 'eeee…'
  ```
  → 파일 절대 경로 ≤ 259, 폴더 절대 경로 ≤ 247(UTF-16).

### d. 지금 코드(base 918b59d2)의 기준선 경로
- devpipe.py:860-861 `baseline_cache_path` (`<base>-py<ver>.json`, 방식 표시 없음) · :864-880 `remove_temp_worktree` · :883-918 `ensure_baseline` · **:897 `git(repo, "worktree", "add", "--detach", str(temp), base)`**.
- dev-run.ps1:318-319 `baseline`(동기, Builder 앞에서 끝까지 기다림) → :323-324 `snapshot-includes` → :326-328 Builder 1회차 → :330-332 check 루프. preflight(devpipe.py:1066-1141)에 경로 길이 검사는 없다.

## 2. 바꾼 파일과 줄

바뀐 파일 7개 + 이 보고 1개(모두 2절 허용 경로 안). `git diff --stat`: test_dev_pipeline.py +489 · dev-run.ps1 +200 · devpipe.py +490/−54(합계) · README.md 12 · judge-prompt.md +1 · register-dev-tasks.ps1 5 · dev-queue.ps1 2.
바꾸지 않음: settings.json · .gitignore · dev-merge.ps1 · builder-rules.md · authority-paths.txt · commit-docs.ps1 · run-docs-commit.ps1.

### D1 경로 길이 preflight
- devpipe.py:77-82 상수 `MAX_FILE_PATH = 259`, `MAX_DIR_PATH = 247`(근거 주석: NUL 포함 260, 폴더 MAX_PATH−12, 실측값).
- :365-409 `utf16_len`(UTF-16 코드 단위) · `longest_tracked_paths`(`git ls-tree -r -z --name-only --full-tree <base>`, 파일·폴더 최장) · `path_budget`(필요 길이 = `<repo>\.claude\worktrees\` + max(id, `_base-<sha8>`) + `\` + 최장 경로; 폴더도 같은 식) · `path_length_check`.
  사유 형식: 파일 `PATH_TOO_LONG:<필요>>259:max_id=<n>`, 폴더 `PATH_TOO_LONG:dir<필요>>247:max_id=<n>`. max_id = 두 한도를 모두 만족하는 최대 이름 길이.
- :1404-1413 `cmd_preflight`: git 검사 바로 뒤, claude CLI 검사 앞에 `PATH_LENGTH`(HEAD 기준). 실패하면 first_failure → `STOP_PREFLIGHT reason=PATH_TOO_LONG:…`(run 모드면 LATEST.json). 모델·기준선·worktree 생성 전이다.
- :1477-1479 `cmd_init_run`: 실제 base로 같은 계산을 다시 해서 넘으면 `STOP_PREFLIGHT`(run 폴더를 만들기 전). run.json에 `path_budget` 기록(:1502).
- README "id는 **14자 이하 권장**(지금 저장소·경로 기준). preflight가 정확히 검사한다 …" 1줄.

### D2 기준선 worktree를 브랜치 위로
- devpipe.py:83-91 `BASE_BRANCH_PREFIX = "devpipe-base-"`, `BASELINE_METHOD = "b2"`, `SHA_RE`.
- :962-967 캐시 이름 `<base>-py<ver>-b2.json`. :989-1003 `cached_baseline`: base·python·**method == b2**가 모두 맞아야 재사용(detached 시절 `…-py3.13.15.json`과 method 없는 파일은 무시).
- :1032-1058 `prepare_baseline_worktree`: 남은 임시 폴더 제거 → 브랜치가 이미 있고 base가 아니면 **STOP_BASELINE base_branch_elsewhere**(-B로 남의 브랜치를 옮기지 않음) → 표지 파일(run 폴더)을 git 실행 **전에** 기록 → **:1048 `git worktree add -B devpipe-base-<sha8> <temp> <base>`** → `symbolic-ref HEAD = refs/heads/devpipe-base-<sha8>`·`HEAD = base` 확인(:1022-1029) → include 파일 복사. 중간 실패는 정리 후 다시 올림.
- :1081-1098 `delete_base_branch`: `git branch -D`는 **① 이름이 devpipe-base- 이름 공간이고 이 base의 이름 ② 이번 실행이 만들었고(branch_created, 만들기 전 없었음) ③ 지금 base를 가리키고 ④ 어느 worktree도 체크아웃하지 않을 때만**. 아니면 kept_* 를 돌려주고 손대지 않는다. 지우는 곳은 이 1곳뿐(:1097).
- :1101-1109 `cleanup_baseline_worktree`(임시 폴더 → 브랜치 순). :1112-1122 `ensure_baseline`(캐시 또는 준비→실행→정리 한 번에; dev-merge의 rebase 재시험 경로가 그대로 씀).
- 기준선 데이터에 `method`, `branch` 기록(:1061-1078).

### D3 기준선을 Builder와 동시에
- devpipe 하위 명령 3개: `baseline-prepare`(:1527, 동기 — 캐시면 `BASELINE OK source=cache …`, 아니면 임시 worktree를 만들고 `BASELINE PENDING branch=… worktree=…`) · `baseline-run`(:1540, 백그라운드 — 전체 스위트·스키마, 캐시·baseline.json 기록, 아무것도 지우지 않음) · `baseline-cleanup --repo --run-dir`(:1553 — 표지 파일을 이 repo·base의 정해진 이름과 대조(:1125-1135, 어긋나면 STOP_BASELINE marker_mismatch), 정리 결과는 별도 파일 baseline-cleanup.json, 두 번 불러도 안전).
- check는 base·python·방식이 같은 baseline.json만 쓴다(:1138-1150): 없으면 `STOP_BASELINE_MISSING`, 다르면 `STOP_BASELINE_MISMATCH`(:1665).
- dev-run.ps1 순서(Invoke-Pipeline :395~): init → 기록 저장 → **:432 baseline-prepare(동기: 임시 worktree를 Builder보다 먼저 만듦 = worktree 동시 생성 없음)** → PENDING이면 `Start-Baseline`(:180, cmd /c 리디렉션 바이트 저장, 로그 `BASELINE start pid=…`) → snapshot-includes → main-snapshot → **:461 Builder 1회차** → Builder 끝 → **:469 `Wait-Baseline`**(:188, 바깥 상한 `$BaselineLimitMinutes = 75` = devpipe 내부 상한 60+10 + 여유 5, 넘으면 트리 종료 → STOP_BASELINE_TIMEOUT; 로그 `BASELINE end exit=… <줄>`) → `Stop-Baseline`(정리) → 실패면 그 STOP 상태로 끝(재시도 없음) → check 루프.
- 모든 종료 경로 정리: `Stop-Baseline`(:210-223: 돌고 있으면 `Stop-ProcessTree` 후 `baseline-cleanup --repo $repo`)을 `Complete-Run` 맨 앞(:366-368), `Stop-RecordChanged` 맨 앞(:247-248), 메인 `finally`에서 `Exit-Lock` 앞(:571-574, try/catch로 감쌈)에서 부른다. Builder TIMEOUT이면 기준선을 트리 종료하고 정리한다. BLOCKED·STOP은 check에서 드러나므로 기준선을 끝까지 기다린 뒤 정리한다.
- 기준선 프로세스는 `.claude/worktrees/_base-<sha8>`에서만 돈다. Builder worktree를 읽거나 쓰지 않고, git 쓰기(정리)는 Builder가 끝난 뒤에만 한다.

### D4 큐 간격 15 → 5분
- register-dev-tasks.ps1:4-5 머리말, :34 `$queueIntervalMinutes = 5`. dev-queue.ps1:1 머리말. 실행 제한 360분·IgnoreNew·commit-docs 900초 + dev-run 340분 + 5 ≤ 360은 그대로(정적 테스트 그대로 통과). 등록은 하지 않았다.

### N1 추가 줄 권한 표지 (올리기만)
- devpipe.py:128-137 `ADDED_VALUE_RE`, `ADDED_NONE_VALUES`; :830-842 `added_value_reasons`; :859 추가 줄마다 호출. 사유 `ADDED_LINE:<key>`.
- 값 = `:` 또는 `=`(`==` 제외) 바로 뒤 토큰. 스키마 `{"const": X}`·`{"type": X}`는 X를 본다. 그 밖의 것(변수, enum, 목록)은 "none 아님"으로 센다.
  `*_approved` = true → authority. `quantity_authority` ∉ {none, null, "none", None, $null} → authority. `execution_quantity` ∉ {null, None, "null", $null} → authority.
- 내리는 경로 없음(`escalate` 그대로).

### N2 문서
- README.md "테스트" 줄에 `` `expected failures` 증가 `` 추가 + "= 실패(재시도 대상)".
- judge-prompt.md:22 G6 다음 줄 1개 추가: "`expected failures` 증가(`@expectedFailure`로 실패를 숨김) = 실패(재시도 대상). checks.json에는 `EXPECTED_FAILURES_INCREASED`로 적힌다." 다른 문장은 그대로.

### O3 메인 체크아웃·run 기록 보호 (좁게)
- a. devpipe `records`(:1568, :1153-1180): run.json · baseline.json · 기준선 캐시 · baseline-worktree.json · main-before.json의 sha256. dev-run이 기록 단계(init-run, baseline-prepare, snapshot-includes, main-snapshot, 기준선 끝) 뒤 `Save-Records`(:226)로 **프로세스 메모리**에 담는다. 그 밖의 모든 단계(baseline-prepare, snapshot-includes, main-snapshot, builder-1, baseline-wait, check-N, judge-prep-N, judge-N, parse-judge-N, fix-prep-1, builder-2, write-result) 직전에 `Test-Records`(:236)가 `--expect name=sha256`로 대조한다. 어긋나거나 사라지면 `STOP_RUN_RECORD_CHANGED reason=<단계>:<파일>`. run.json을 믿을 수 없으므로 write-result 대신 write-latest(dev-run의 $repo·$Id)로만 남긴다(result.json 없음 → 병합 불가).
- b. devpipe `main-snapshot`(:1582)·`main-compare --name check-N`(:1591), 함수 `main_snapshot`(:1199: `git --no-optional-locks status --porcelain -z --untracked-files=no --no-renames` 중 docs/claude/ 밖 줄 + workspace/policies/·stock-strategy-system/ 아래 모든 파일(추적·무시) sha256), `compare_main`(:1222: **새로 나타난 상태 줄**과 바뀐·생긴·사라진 감시 파일). Builder 1회차 직전 찍고 check-1·check-2 직전마다 비교 → `STOP_MAIN_TOUCHED reason=<경로>`(재시도 없음). 실행 전부터 있던 변경, docs/claude/ 줄, HEAD 이동(문서 커밋)은 무시한다.
- 06:10~06:40 KST(:1185 `auto_core_window_overlaps`, 찍은 시각~비교 시각이 어느 날이든 그 구간에 닿으면)에는 **stock-strategy-system/ 비교(파일 sha256·상태 줄)만** 건너뛰고 `MAIN OK … skipped=SKIPPED_AUTO_CORE_WINDOW`(log와 main-check-N.json). 정책 파일·다른 추적 파일 비교는 그대로다. **fail-closed가 아닌 예외다.**

## 3. 테스트 수치

| 대상 | 결과 |
|---|---|
| test_dev_pipeline.py | **Ran 118 OK**(편집 전 86 OK → +32, 삭제·약화 0). 시간 105초 → 146~159초(측정 3번) |
| 기존 settings 검사 3파일 | test_auto_core* Ran 89 OK · test_reconcile_broker_state* Ran 56 OK · test_portfolio_exposure_judge_fixes* Ran 29 OK |
| 스키마 감사 | `validate_schema_contracts.py` exit 0, status PASS |
| 전체 스위트 | 편집 뒤 18:53:13→18:59:01, `PYTHONDONTWRITEBYTECODE=1`, test-runner가 원본 바이트 저장 → 직접 비교: **Ran 2678 → 2710(+32) · `FAILED (failures=19, errors=9, skipped=2)` 그대로 · 실패 id 28 = 0단계 a의 28과 같은 집합(새 실패 0, 사라진 것 0) · skipped 2 → 2** |
| .ps1 위생 | 6개 모두 비ASCII 0 · CRLF only · 파서 오류 0. 바뀐 파일 모두 CRLF 유지(LF only 0) |

새 테스트(32개):
- PathLengthTests(8): UTF-16 단위(한국어 1, 서로게이트 2) · 파일 경계 259 통과/260 거절 · 폴더 경계 247/248 · 기준선 이름 포함 · 이 PC 값(10자 255 통과, 28자 `PATH_TOO_LONG:269>259:max_id=18`) · 최장 경로를 base의 추적 목록에서 셈(추적 안 된 파일·뒤 커밋 제외) · preflight가 CLI 검사 전에 `PATH_TOO_LONG`(worktree·_baseline 없음) · init-run도 멈춤.
- BaselineBranchTests(6): 임시 worktree `branch --show-current = devpipe-base-<sha8>` · 정리 뒤 worktree·브랜치 0, Builder worktree·다른 브랜치 그대로 · 캐시 키 -b2, devpipe-base-other·feature-x 그대로 · detached 시절 캐시 재사용 안 함 · 이미 있던 브랜치 유지 · 다른 커밋을 가리키면 STOP(옮기지 않음) · 삭제 규칙.
- BaselineStepTests(4): prepare→run→cleanup(run은 지우지 않음, cleanup 두 번 안전, 다음 실행 캐시) · Builder 실패 경로 정리 + 기준선 없을 때 check `STOP_BASELINE_MISSING` · 표지가 다른 곳을 가리키면 거절 · 다른 base·method·python 기준선 거절.
- AddedLineMarkerTests(3), RunRecordTests(2), MainCheckoutTests(5: 손대지 않음·기존 변경 통과 / 정책·상태(추적·무시)·새 정책 파일·추적 코드 파일 변경 STOP / docs/claude 변경·문서 커밋 통과 / 시간대 예외는 상태만 / 시간대 경계).
- StaticScriptTests +4: dev-run 순서(prepare → Start-Baseline → snapshot → main-snapshot → Builder 1 → Wait-Baseline → main-compare → check), 정리 위치, 단계별 기록 대조, `branch -D`는 delete_base_branch 1곳과 그 앞 조건, `--detach` 없음, 문서 줄. 기존 정적 테스트의 큐 간격 숫자 15 → 5.

## 4. Windows 실측 (모델 호출 없음)

① PowerShell 5.1 파서(`[System.Management.Automation.Language.Parser]::ParseFile`):
```
commit-docs.ps1 parse_errors=0
dev-merge.ps1 parse_errors=0
dev-queue.ps1 parse_errors=0
dev-run.ps1 parse_errors=0
register-dev-tasks.ps1 parse_errors=0
run-docs-commit.ps1 parse_errors=0
```
② `powershell -ExecutionPolicy Bypass -File tools\register-dev-tasks.ps1 -PlanOnly` (exit 0, worktree에서 실행해 경로는 worktree. 등록 안 함):
```
TASK_NAME = InvestmentV2-DevQueue
MODE = PLAN_ONLY
TRIGGER = every 5 minutes, no end
TRIGGER_START_BOUNDARY = 2026-10-09T15:00:00Z
TRIGGER_REPETITION = interval=PT5M duration=INDEFINITE
WINDOWS_TIMEZONE = Korea Standard Time
TIMEZONE_READY = True
RUN_LEVEL = LIMITED
LOGON_TYPE = INTERACTIVE
START_WHEN_AVAILABLE = True
WAKE_COMPUTER = False
EXECUTION_LIMIT_MINUTES = 360
MULTIPLE_INSTANCES = IGNORE_NEW
LAUNCHER = CONHOST_HEADLESS
TASK_EXISTS_BEFORE = YES
TASK_EXISTS_AFTER = YES
ORDER_AUTHORITY = False
```
(DocsCommit: daily 23:30 · 15분 · IGNORE_NEW 그대로. 출력의 두 이름 외 작업 없음.)

③ devpipe 경로 길이 계산, 이 PC 메인 경로 `E:\사업\##금동한\코덱스저장소` + base 918b59d2의 추적 목록:
```
id=t3b-check1 (10 chars) -> {"need_file": 255, "need_dir": 171, "max_id": 18, "longest_file": 203, "longest_dir": 119, "reason": null}
id=t3-trial-prompt-profile-test (28 chars) -> {"need_file": 269, "need_dir": 185, "max_id": 18, "longest_file": 203, "longest_dir": 119, "reason": "PATH_TOO_LONG:269>259:max_id=18"}
base=918b59d2 baseline_name=_base-918b59d2 main_utf16=18 calc_seconds=0.106
```

## 5. Builder 판단 목록

1. **D1 폴더 한도 추가**: 지시문 식은 파일만 셌다. 실측에서 폴더 248이 거절되어(git `cannot create directory`) 폴더 247 검사를 더했다. 더 엄격해지기만 한다(지금 저장소는 폴더 171로 여유).
2. **D1 위치**: preflight는 원래대로 검사를 모두 모은다(CLI 검사를 건너뛰지 않음). 경로 계산 자체는 0.1초. STOP은 같은 preflight 단계에서 나온다(모델·기준선·worktree 전). preflight 전체에는 `claude --version/--help`(몇 초)가 들어 있다. init-run에서 실제 base로 한 번 더 본다.
3. **D2 이미 있는 브랜치**: `devpipe-base-<sha8>`가 이미 base에 있으면 -B(변화 없음)로 쓰되 "이번 실행이 만든 것"이 아니므로 지우지 않는다. 다른 커밋을 가리키면 옮기지 않고 STOP_BASELINE.
4. **D2 삭제 명령**: 지시문대로 `git branch -D`를 쓰고, 그 앞에서 이름 공간·생성 여부·base 가리킴·체크아웃 여부를 확인한다. 확인과 삭제 사이 원자성은 없다(자기 이름 공간 안의 아주 짧은 틈).
5. **D3 정리 시점**: 백그라운드 기준선 프로세스는 아무것도 지우지 않는다. 정리(git 쓰기)는 Builder가 끝난 뒤 dev-run이 한다(Claude Code가 일하는 동안 git 쓰기 겹침 방지). Builder TIMEOUT이면 기다리지 않고 트리 종료.
6. **D3 표지 파일**: git 실행 전에 기록해 중간 실패도 정리 대상이 된다. 정리는 `--repo`를 dev-run에서 받고 표지를 정해진 이름과 대조한다(바뀐 run.json이 정리 대상을 다른 곳으로 돌리지 못하게).
7. **D3 check 입력 고정**: check는 base·python·방식이 같은 baseline.json만 받는다(MISSING/MISMATCH STOP). 지시문의 "기다리거나 STOP" 중 STOP.
8. **D3 바깥 상한 75분**: devpipe 내부 상한(60+10분)은 그대로이고, 기준선 프로세스가 멈춘 경우만 잡는다.
9. **O3a 구현 방식**: 해시 계산은 devpipe `records`, 기대값은 dev-run 메모리(인자로 넘김). 테스트할 수 있게 하려는 것이다. 대상에 run.json·캐시 외에 baseline.json(check가 실제로 읽는 사본)과 표지 파일 2개를 더했다. STOP 때는 write-result 대신 write-latest만.
10. **O3b 범위**: 새로 나타난 상태 줄만 센다(사라진 줄 = 커밋·되돌림은 무시 — "시작 전 변경은 대상 아님"). `--no-optional-locks`로 메인 index를 건드리지 않는다. 시간대 예외는 stock-strategy-system/의 파일 해시와 상태 줄 모두에 걸린다(상태 줄도 빼지 않으면 06:15 기록이 추적 파일 변경으로 잡힘). 정책·다른 추적 파일 비교는 그대로. 시각이 뒤집히면 예외 없음(엄격).
11. **N1 값 규칙**: `{"const": X}`·`{"type": X}`를 들여다보고 `$null`(PowerShell)을 null로 본다. `quantity_authority: false`는 지시문 그대로 "none 아님" → authority(오탐 쪽, 기존 추적 줄 약 30곳에 이 형태가 있음). 비교식(`==`), 값 없는 키, 표 칸은 안 잡는다.
12. **테스트 시간**: 새 git 픽스처 테스트로 test_dev_pipeline이 약 +40~50초(전체 스위트의 약 12%). 기록·메인 테스트는 가벼운 저장소로 줄였다.
13. **0단계 a**는 원본 출력에서 직접 세려고 직접 실행했다. 마지막 전체 스위트는 test-runner 서브에이전트가 원본 바이트를 파일로 남기게 하고, 실패 집합은 그 파일에서 내가 직접 비교했다.

## 6. 남는 위험

- **강제 종료 잔여물**: dev-queue 340분 상한·전원 차단으로 dev-run 프로세스 트리가 죽으면 `_base-<sha8>` 폴더와 `devpipe-base-<sha8>` 브랜치가 남을 수 있다. 같은 base의 다음 실행은 폴더를 지우지만 브랜치는 "이번 실행이 만든 것"이 아니라 남긴다(규칙대로). 해롭지 않고 `git branch --list "devpipe-base-*"`로 보인다. 자동 청소는 없다.
- **O3는 좁다**: 같은 사용자 권한의 코드는 감시 폴더 밖(추적 안 된 파일, 저장소 밖)에 쓸 수 있다. 실행 전부터 수정돼 있던 추적 파일을 더 바꾸면 상태 줄이 같아 못 잡는다. 06:10~06:40 예외 구간의 상태 파일 변경은 못 잡는다(fail-closed 아님). 반대로 실행 중 Cowork가 대조 apply·저널 apply를 하면 STOP_MAIN_TOUCHED 오탐이다(fail-closed, 새 id로 다시).
- **D3 동시 실행**: 기준선과 Builder 세션의 테스트가 CPU를 나눈다. 테스트가 고정 공유 경로에 쓰는 곳은 찾지 못했다(tests grep: mkdtemp만, `Path.home()`은 읽기). check 때 전체 스위트는 기준선이 끝난 뒤 혼자 돈다. BLOCKED·STOP Builder도 check까지 기준선을 기다린다(기준선 시간만큼, 이전과 같은 수준).
- **N1 오탐**: 새 코드·보고서에 `quantity_authority: false`, 변수 대입, 비 null 수량 예시가 있으면 NEEDS_APPROVAL(사용자 1번). 안전 쪽.
- **dev-merge rebase 경로**도 이제 브랜치 기준선을 쓴다(ensure_baseline). dev-run과 같은 base로 동시에 돌면 `_base-<sha8>`가 겹칠 수 있는 점은 이전과 같다.
- 큐 5분 = 시간당 숨김 실행 12번(heartbeat 갱신). 저장소 경로가 길어지면 max_id가 줄어든다(preflight가 잡음).
- 완료 기준 ②③(큐→Builder ≤ 6분, BASELINE과 BUILDER 로그 겹침)과 ①의 실측(기준선 실패 28)은 병합 뒤 첫 파이프라인 작업에서 확인한다(지시문 4절).
