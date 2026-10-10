---
id: redesign-t3-builder-report-2026-10-10
title: 재설계 T3 Builder 보고 — 한 줄 개발 파이프라인(dev-run · dev-merge · 큐) + 문서 자동 커밋
date: 2026-10-10
prompt: docs/claude/redesign-t3-builder-prompt-2026-10-10.md (1~3절)
worktree: .claude/worktrees/redesign-t3 (브랜치 worktree-redesign-t3, base d7d5292)
builder: Claude Code 2.1.296 · Opus 5.5 · Windows 11 · PowerShell 5.1.26100.9444
authority: order_authority=false · quantity_authority=none · execution_quantity=null (개발 절차만. 주문·정책·상태·브로커 경로 무관)
consumers: T3 Judge(5절) · Cowork(병합·작업 등록·CLAUDE.md 반영·첫 시험) · 관제판 redesign-t3
---

# 재설계 T3 Builder 보고

**BLOCKED 없음.** 커밋·병합·push·Windows 작업 등록·모델을 부르는 `claude -p` 실행 없음. 키움 조회·주문 없음. 비밀 파일 읽기 없음.

## 1. 0단계 사실 확인

### a. `claude --version` / `claude --help` (설치본 `C:\Users\…\.local\bin\claude`, **2.1.296 (Claude Code)**)

| 플래그 | --help | 정확한 철자 | 허용 값 (help 원문) |
|---|---|---|---|
| -p | 있음 | `-p, --print` | — |
| --worktree | 있음 | `-w, --worktree [name]` | — |
| --model | 있음 | `--model <model>` | 별칭(`fable`, `opus`, `sonnet`) 또는 전체 이름 |
| --effort | 있음 | `--effort <level>` | low, medium, high, **xhigh**, max |
| --permission-mode | 있음 | `--permission-mode <mode>` | **acceptEdits**, auto, bypassPermissions, manual, dontAsk, plan |
| --permission-prompts | 있음 | `--permission-prompts <target>` | host, **none** (기본 host). none = "anything that would prompt is denied automatically" |
| --max-turns | **없음** (help에 안 나옴) | `--max-turns` | — (아래 근거) |
| --output-format | 있음 | `--output-format <format>` | text, **json**, stream-json |
| --tools | 있음 | `--tools <tools...>` | `""`, `default`, 도구 이름 목록 |
| --allowedTools | 있음 | `--allowedTools, --allowed-tools <tools...>` | 쉼표·공백 구분 목록 |
| --strict-mcp-config | 있음 | `--strict-mcp-config` | — |
| (추가 사용) --setting-sources | 있음 | `--setting-sources <sources>` | user, **project**, local |
| (추가 사용) --disallowedTools | 있음 | `--disallowedTools, --disallowed-tools <tools...>` | — |

- `--max-turns`: help에는 없지만 공식 CLI 문서에 있다 — "Limit the number of agentic turns (print mode only). Exits with an error when the limit is reached." 같은 문서: "`claude --help` does not list every flag, so a flag's absence from `--help` does not mean it is unavailable." (code.claude.com/docs/en/cli-reference).
- 실제 설치본이 이 철자를 아는지는 **모델을 부르지 않는 파서 검사**로 확인했다:
  - `claude --version` 검사는 쓸모없음: `claude --no-such-flag-xyz 1 --version`도 `2.1.296` 출력, exit 0.
  - 파서는 첫 미지 옵션에서 멈춘다: `claude --aaa-bogus 1 --bbb-bogus -p` → `error: unknown option '--aaa-bogus'` (exit 1).
  - `claude --max-turns 1 --no-such-flag-xyz -p` → `error: unknown option '--no-such-flag-xyz'` (exit 1) → `--max-turns`는 알려진 옵션.
  - 이 호출들은 옵션 해석 단계에서 끝나 프롬프트를 읽지 않는다(stdin = NUL). 모델 호출 없음.
- 대체 플래그로 바꿔 쓴 것 없음. preflight 판정 규칙(판단 1): 필수 플래그는 help에 있어야 하고, 예외는 상수 `HELP_HIDDEN_DOCUMENTED_FLAGS = ("--max-turns",)`뿐이다. 예외도 위 파서 검사(`claude --max-turns 1 --zz-devpipe-probe -p`)가 `unknown option '--zz-devpipe-probe'`를 내야 통과다. 아니면 `CLI_FLAG_MISSING:--max-turns`로 멈춘다.

### b. `-p` + `--worktree <name>` (문서 근거, code.claude.com/docs/en/worktrees)
- 경로 `<repo>/.claude/worktrees/<name>`, 브랜치 `worktree-<name>`. 기존 목록(이 worktree 포함)과 같다.
- `worktree.baseRef = "head"`: "branch from your current local HEAD".
- `-p`는 정리하지 않는다: "Non-interactive runs with `-p` have no exit prompt, so Claude doesn't clean up their worktrees, and Claude Code leaves the lock it took on each one at creation in place". 변경이 없어도 남는다.
- 같은 이름 폴더가 있으면 "opens that existing worktree instead of creating a new one" → preflight가 같은 id의 run 폴더·worktree·브랜치를 거절한다.
- 실제 경로·브랜치·HEAD는 P1 검사 ①이 매번 확인한다. `git worktree list` 등록, 브랜치 `refs/heads/worktree-<id>`, `--show-toplevel`, HEAD = base를 본다.
- 이 worktree에서 관찰: Claude Code가 새 worktree에 `.worktreeinclude` 목록(`stock-strategy-system/portfolio_state.json`, `alert_runtime_state.json`)과 `.claude/settings.local.json`을 복사했다(메인 사본과 sha256 같음). 이 때문에 검사 ③에 예외 처리를 넣었다(판단 4).

### c. `--output-format json` 최상위 필드
- CLI 문서가 이름을 대는 필드: `result`, `session_id`, `total_cost_usd`(+ `--json-schema` 때 `structured_output`). 실패하면 exit ≠ 0, "prints the failure as the result on stdout".
- `type`·`subtype`(success, error_max_turns, error_during_execution …)·`is_error`·`num_turns`는 Agent SDK 결과 메시지 문서에 있다. CLI json이 같은 객체라는 문장은 문서에 없다 → **확인 필요(첫 시험)**.
- 파서는 fail-closed다. `is_error`가 정확히 `false`가 아니면 JUDGE_ERROR다. `subtype`가 있으면 `success`여야 한다.

### d. 권한 규칙 (code.claude.com/docs/en/permissions, permission-modes, headless)
- 문법: `Bash(git diff *)` ≡ `Bash(git diff:*)`. `*` 앞 공백도 규칙의 일부다. PowerShell 규칙도 같은 모양이다. 복합 명령(`&&`, `;`, `|` …)은 하위 명령마다 따로 맞아야 한다.
- 순서: "Rules are evaluated in order: deny, then ask, then allow." "If a tool is denied at any level, no other level can allow it … a managed settings deny can't be overridden by `--allowedTools`". "Deny rules block in every mode". ask는 어떤 모드에서도 자동 승인되지 않는다("Tools matched by an explicit ask rule"). `--permission-prompts none`은 묻는 것을 거절한다 → settings의 deny·ask가 `--allowedTools`·acceptEdits보다 먼저다(ask는 묻기라서 거절된다는 것은 문서 문장으로부터의 추론).
- `/` 경로: "`/path` | Path relative to the settings source"(프로젝트 설정 = primary working directory). "in a worktree session, a shared rule such as `Edit(/src/**)` matches that worktree's own `src/` directory." → P9의 `Edit(/.claude/settings.json)` 등은 각 세션 작업 폴더(worktree) 기준이다.
- 한계(문서): deny·ask는 "isn't a security boundary around the program"(다른 형태 호출은 못 막음) → P1 ③④가 사후에 다시 막는다.

### e. 테스트 기준선 (이 worktree, 변경 전 clean, base d7d5292, Python 3.13.15, `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`)
- 명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"` (원본 출력에서 직접 셈)
- `Ran 2584 tests in 243.993s` · `FAILED (failures=19, errors=9, skipped=2)` → 실패 id 28개(아래). T1 r3 기록(Ran 2584, 실패 28)과 같다.

<details><summary>기준선 실패 id 28개</summary>

```
ERROR: setUpClass (test_holding_baseline_observation_audit.HoldingBaselineObservationAuditTests)
ERROR: setUpClass (test_mvll_canonical_volume_lineage.MvllCanonicalVolumeLineageTests)
ERROR: setUpClass (test_provider_limitation_audit.ProviderLimitationAuditTests)
ERROR: test_05_materialized_candidate_passes_binding_validator (test_materialize_kiwoom_session_aware_acceptance_candidate…)
ERROR: test_live_price_artifact_schema_and_semantics (test_nbis_v4_kiwoom_price_authority…)
ERROR: test_lmt_candidate_classification_is_verified_but_non_actionable (test_portfolio_decision_order_intent…)
ERROR: test_price_evidence_preserves_same_session_kiwoom_conflict (test_nbis_v3_shadow_activation…)
ERROR: test_snapshot_fixture_declares_contract_version (test_validate_research_packet…)
ERROR: test_valuation_uses_kiwoom_and_no_double_count (test_nbis_v4_kiwoom_price_authority…)
FAIL: test_12_allowed_drift_is_recorded_and_validates (test_materialize_kiwoom_session_aware_acceptance_candidate…)
FAIL: test_15_current_fixed_activation_is_exactly_bound (test_instrument_identity_authority…)
FAIL: test_bom_raw_sha_mismatch_rejected (test_v2_6_7_session_aware_kiwoom_priority…)
FAIL: test_candidate_support_does_not_replace_active_registry (test_materialize_instrument_identity_artifact…)
FAIL: test_crlf_raw_sha_mismatch_rejected (test_v2_6_7_session_aware_kiwoom_priority…)
FAIL: test_duplicate_provider_scope_fails_closed (test_v2_6_7_session_aware_kiwoom_priority…)
FAIL: test_extended_provider_scope_candidate_validates_without_activation (test_v2_6_7…)
FAIL: test_guarded_priority_requires_locked_acceptance_manifest (test_v2_6_7…)
FAIL: test_historical_and_inactive_candidate_are_not_current_acceptance (test_v2_6_7…)
FAIL: test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch (test_evaluate_timing_integration…)
FAIL: test_malformed_provider_scope_fails_closed (test_v2_6_7…)
FAIL: test_missing_acceptance_hash_blocks_guarded_transition (test_v2_6_7…)
FAIL: test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan (test_portfolio_decision_dashboard…)
FAIL: test_scope_04_checked_in_provider_scopes_are_complete_and_locked (test_v2_6_7…PriorityAndScopeTests)
FAIL: test_scope_acceptance_hash_mismatch_blocks_guarded_transition (test_v2_6_7…)
FAIL: test_unapproved_provider_symbols_fail_closed (test_v2_6_7…) ×4 (subTest 꼬리가 다른 4개)
```
</details>

### f. python·시간대
- python 찾기는 `run_auto_core.ps1`과 같다: `.venv\Scripts\python.exe` → `venv\Scripts\python.exe` → PATH의 `python.exe` → `python`. 이 PC는 venv 없이 `C:\Users\…\Python313\python.exe`(3.13.15)를 쓴다.
- Windows 시간대 `Korea Standard Time`. git 2.56.0.windows.1, `core.autocrlf=true`(색인 LF, 작업 트리 CRLF).

## 2. 바꾼 파일 · 테스트 · 스키마 · Windows 실측

### 바꾼 파일 (허용 경로 대조 — 전부 안)

| 파일 | 종류 | 허용 경로 |
|---|---|---|
| tools/dev-run.ps1 | 새 파일 (ASCII, CRLF) | ✓ |
| tools/dev-merge.ps1 | 새 파일 (ASCII, CRLF) | ✓ |
| tools/dev-queue.ps1 | 새 파일 (ASCII, CRLF) | ✓ |
| tools/run-docs-commit.ps1 | 새 파일 (ASCII, CRLF) | ✓ |
| tools/register-dev-tasks.ps1 | 새 파일 (ASCII, CRLF) | ✓ |
| tools/dev_pipeline/devpipe.py | 새 파일 (UTF-8, 표준 라이브러리만) | ✓ |
| tools/dev_pipeline/builder-rules.md · judge-prompt.md · authority-paths.txt · README.md | 새 파일 | ✓ |
| manage-us-stock-strategy/tests/test_dev_pipeline.py | 새 파일 | ✓ |
| docs/claude/redesign-t3-builder-report-2026-10-10.md | 이 보고 | ✓ |
| .gitignore | **+2 / −0** (`workspace/outputs/dev-runs/`, `docs/claude/_dev-queue/`), CRLF | ✓ |
| .claude/settings.json | **+12 / −0** (P9: deny 8 + ask 4, 배열 맨 앞에 끼움 → 기존 줄 변경 0), CRLF, allow 없음 | ✓ (마지막 편집) |
| tools/commit-docs.ps1 | **변경 없음** (무인 실행에 고칠 것이 없었다) | — |

workspace/policies/*, stock-strategy-system/*, CLAUDE.md, AGENTS.md 변경 0.

### 테스트
- 대상: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline*.py"` → **Ran 81, OK** (P9 편집 뒤).
- settings 검사 기존 테스트 (P9 뒤): `test_auto_core*` Ran 89 OK · `test_reconcile_broker_state*` Ran 56 OK · `test_portfolio_exposure_judge_fixes*` Ran 29 OK.
- 전체 스위트(P9 뒤, 같은 조건 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`): `Ran 2665 tests in 318.201s` · `FAILED (failures=19, errors=9, skipped=2)`.
  - 실패 id 집합 = 기준선 28개와 **같음**: 새 실패 0, 고쳐진 것 0.
  - Ran 2584 → 2665(+81 = test_dev_pipeline), skipped 2 → 2.
  - 비교는 devpipe.py의 `parse_unittest_output` + `evaluate_tests`로 했고, 결과는 `None []`이다.
- 스키마 감사 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → `"status": "PASS"`, exit 0.

### Windows 실측 (이 세션, 모델 호출 없음, P9 편집 전) — 원문
1. `powershell -File tools\dev-run.ps1 -Preflight t3-probe-none` → exit 2
   `DEV-RUN t3-probe-none STOP_PREFLIGHT reason=NOT_MAIN_CHECKOUT claude=2.1.296 flags=13/13 report=workspace/outputs/dev-runs/_preflight/t3-probe-none.json`
   (worktree에서 돌렸으므로 메인 체크아웃 검사가 첫 실패. 같은 보고서의 다른 검사: `PROMPT_COMMITTED FAIL PROMPT_NOT_COMMITTED`, `ID_UNUSED OK`, `MAIN_NO_STAGED OK`)
2. 같은 preflight 보고서의 플래그 검사 — 0단계 a와 같다:
   `CLI_FLAG:-p help · --worktree help · --model help · --effort help · --permission-mode help · --permission-prompts help · --max-turns probe · --output-format help · --tools help · --allowedTools help · --strict-mcp-config help · --setting-sources help · --disallowedTools help` (13/13 OK), `CLAUDE_VERSION OK min=2.1.296`
3. `powershell -File tools\register-dev-tasks.ps1 -PlanOnly` → exit 0 (등록 안 함)
   `TASK_NAME = InvestmentV2-DocsCommit · MODE = PLAN_ONLY · TRIGGER = daily 23:30 local (KST) · TRIGGER_START_BOUNDARY = 2026-10-10T14:30:00Z · WINDOWS_TIMEZONE = Korea Standard Time · TIMEZONE_READY = True · RUN_LEVEL = LIMITED · LOGON_TYPE = INTERACTIVE · START_WHEN_AVAILABLE = True · WAKE_COMPUTER = False · EXECUTION_LIMIT_MINUTES = 15 · MULTIPLE_INSTANCES = IGNORE_NEW · LAUNCHER = CONHOST_HEADLESS · EXECUTE = C:\WINDOWS\System32\conhost.exe · ARGUMENTS = --headless "…\powershell.exe" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "…\tools\run-docs-commit.ps1" · TASK_EXISTS_BEFORE = NO`
   `TASK_NAME = InvestmentV2-DevQueue · TRIGGER = every 15 minutes, no end · TRIGGER_REPETITION = interval=PT15M duration=INDEFINITE · EXECUTION_LIMIT_MINUTES = 360 · (나머지 같음) · TASK_EXISTS_BEFORE = NO`
4. `powershell -File tools\run-docs-commit.ps1 -DryRun` → exit 0, 커밋 없음
   `NOTHING: no docs\claude\_pending folder.` / `== exit=0` (`workspace/outputs/docs-commit/2026-10-10.log` 106바이트)

추가 확인(모델 호출 없음): 5개 .ps1 PowerShell 파서 오류 0. `dev-merge.ps1 t3-probe-none` → `DEV-MERGE t3-probe-none STOP_NOT_MAIN_CHECKOUT reason=repo` (exit 2). `dev-queue.ps1` → exit 0, `QUEUE EMPTY`. `conhost.exe --headless powershell.exe …` → exit 0, 파일 기록 확인. 전체 스위트 실행 뒤에도 worktree의 복사 파일 3개 sha256 = 메인 사본(테스트가 바꾸지 않음).

### P7 권한 경로 근거 (grep, 파일:줄)

| 경로 | 범주 | 근거 |
|---|---|---|
| scripts/auto_core*.py | 대조 불변 조건·정지 스위치 | auto_core_reconcile.py:40 `AUTO_CORE_INVARIANTS`, :921 `def run_auto(*, mode, kill_switch …` |
| scripts/apply_user_confirmed_broker_snapshot.py | 불변 조건·정지 스위치 | :33 `AUTO_CORE_INVARIANTS = ("I1".."I5")`, :375 `if config["kill_switch"] is not False:` |
| scripts/reconcile_broker_state.py | 정지 스위치 | :359 `"kill_switch": "KILL_SWITCH_ON" in reasons` |
| scripts/kiwoom_broker_shadow.py | 불변 조건(I5) | :31 `NEVER_TOUCHED_FIELDS = ("current_stage", "timing_plan", …` |
| scripts/cash_flow_evidence.py · assets/kiwoom-transaction-history-classification.json | 불변 조건(I3) | cash_flow_evidence.py:31 `CLASSIFICATION_PATH = … kiwoom-transaction-history-classification.json` |
| schemas/auto-core-config.schema.json | 정지 스위치·모드 | :5 "Only a person changes this file. compare never writes state; apply …" |
| assets/kiwoom-acceptance-pin-scope.json | 불변 조건(보호 경로 목록 원천) | auto_core_reconcile.py가 읽어 guarded path를 만든다(T1) |
| references/broker-snapshot-reconciliation.md · docs/claude/automation-redesign-2026-10-10.md | 불변 조건 정의 문서 | CLAUDE.md "every invariant in … 3-5", "read … broker-snapshot-reconciliation.md" |
| scripts/run_auto_core.ps1 · register_auto_core_task.ps1 · collect_30m.ps1 | auto-core 진입점·등록·조회 | 지시문 후보. collect_30m.ps1:1 "Read-only Kiwoom 30-minute bar collection (kiwoomcli …)" |
| scripts/kiwoom_*bridge*.py | 주문 도구 차단 | kiwoom_runtime_bridge.py:29 `BLOCKED_TERMS = {"order", …}`, kiwoom_candidate_discovery_bridge.py:50 `blocked_api_ids`, kiwoom_account_readonly_bridge.py:22 허용 목록 |
| scripts/future_order_shadow.py | 주문 경로 | :13 `ORDER_PATHS = {"/api/us/ordr"}` |
| scripts/portfolio_decision_order_intent.py | 주문 의도·상한 | :317 `risk.get("hard_cap_violations")` |
| scripts/portfolio_decision_dashboard.py | 주문 단계·상한 | :1093 레버리지 상한 규칙, `stage2_firewall` |
| scripts/shadow_acceptance.py · staged_promotion.py · validate_new_buy_strategy_draft.py · validate_decision_record.py | 주문 권한 게이트 | shadow_acceptance.py:293 `ORDER_AUTHORITY_TRUE`, staged_promotion.py:42, validate_new_buy_strategy_draft.py:20 `ORDER_AUTHORITY_PROHIBITED`, validate_decision_record.py:178 |
| schemas/strategy-evolution-policy.schema.json | 권한 상한 | :5 `evolution_authority_ceiling` |
| scripts/portfolio_exposure.py · run_portfolio_exposure_review.py | 노출 상한·종목 상한 | portfolio_exposure.py:159 `hard_ceiling_when_exposure_gte`, :981 `SINGLE_STOCK_CAP`; run_…:50 `DEFAULT_POLICY = …alert_policy.json` |
| scripts/portfolio_policy_gates.py · build_capital_redeployment_plan.py | 예산(집행 가능 금액) | :89 `execution_purchasing_power_usd`, :61 |
| scripts/evaluate_alerts.py · validate_research_packet.py · assets/portfolio-decision-risk-envelope-v0.2.json | 상한·승인 밴드 | :1123 `approved_bands`, :585 "proposed buy exceeds verified available cash", risk-envelope :15 `"hard_cap_pct": 20.0` |
| scripts/run_tactical_opportunity_radar.py · screen_tactical_candidates.py · validate_registry_consistency.py · build_new_buy_*.py | 승인 상품 | :46/:85 `watchlist_approved`, :14 `CRITICAL_FIELDS`, :54/:20 `new_buy_instrument_approved` |
| tests/test_auto_core*, test_reconcile_broker_state*, test_future_order_shadow*, test_portfolio_decision_order_intent*, test_portfolio_exposure*, test_run_portfolio_exposure_review* | 위 코드의 테스트 | 불변 조건·상한 테스트 약화도 승인 대상 |

빠진 것: `order_authority`가 false인지 보기만 하는 작은 스크립트 약 57개. 이 파일들은 목록에 넣지 않았다. 대신 판단 7의 줄 표지로 덮는다. `workspace/policies/**`·`stock-strategy-system/**`(alert_policy.json의 상한·stages·approved_bands 포함)는 보호 경로라서 파이프라인이 아예 못 고친다.

## 3. Builder가 판단한 것 (Judge가 하나씩 수용/거부)

1. **`--max-turns` 처리**: help에 없다. 공식 문서와 파서 검사(1-a)로 인식을 확인했고, preflight도 같은 검사를 매번 한다. 다른 플래그로 바꿔 쓰지 않았다. 거부하면 상수 `HELP_HIDDEN_DOCUMENTED_FLAGS`를 비우면 된다 → preflight가 늘 `CLI_FLAG_MISSING:--max-turns`로 멈춘다(파이프라인 정지).
2. **더 좁히는 플래그 추가**(모두 preflight 필수 플래그 목록에 넣음):
   - `--setting-sources project`: 사용자·local 설정의 allow를 싣지 않는다. 지금 local에 `Bash(cd *)`가 있고, 나중에 넓은 allow가 생겨도 P8을 넘지 못한다.
   - `--disallowedTools "mcp__*"`: 문서상 `--tools`는 MCP에 영향이 없고 `--strict-mcp-config`가 claude.ai 커넥터를 명시하지 않아서 더했다.
   - Builder `--tools "Read,Edit,Write,Grep,Glob,Bash,PowerShell"`: WebFetch·WebSearch·Agent를 뺀다.
3. **보호 경로 확장**(P6 ⊂ 상수):
   - `.worktreeinclude`를 더했다(미래 worktree로 복사될 파일을 정함).
   - `CLAUDE.md`·`CLAUDE.local.md`·`AGENTS.md`·`.mcp.json`·`.gitignore`·`.gitattributes`·`.worktreeinclude`는 **어느 깊이든** 보호한다. Claude Code가 하위 폴더 CLAUDE.md를 읽어 Judge에 지시를 심을 수 있고, 하위 .gitignore는 새 파일을 범위 검사에서 숨길 수 있다.
   - 어느 깊이든 `.claude` 폴더도 보호한다. 비교는 대소문자를 무시한다(Windows).
   - allowed_paths 겹침 거절은 고정 위치 규칙으로 하고, 어느 깊이 규칙은 검사 ③이 막는다.
4. **worktree 복사 파일 예외**: Claude Code가 `.worktreeinclude` 목록과 `.claude/settings.local.json`을 새 worktree에 복사한다(1-b 관찰). 그대로면 모든 실행이 STOP_PROTECTED가 된다.
   - Builder 시작 직전 메인 사본 sha256을 run.json `include_snapshot`에 적고, 같을 때만 변경으로 보지 않는다.
   - `__pycache__/*.pyc`도 예외다(.claude 아래 제외).
5. **무시되는 코드 파일**: 어디든 `.py`·`.pth`·`.pyd`나 `__pycache__` 밖 `.pyc`가 새로 생기면 STOP_SCOPE다.
   - 파이프라인 테스트는 `PYTHONDONTWRITEBYTECODE=1`과 매번 새 `PYTHONPYCACHEPREFIX`로 돈다. Builder가 만든 무시 파일이나 바이트코드가 판정 테스트 결과를 바꾸지 못한다.
6. **위생 결과 분류**:
   - CRLF 깨짐·.ps1 비ASCII → RETRYABLE(수정 1회로 고칠 수 있음).
   - 비밀 같은 파일 이름 → STOP_SECRET(재시도·Judge 없음).
   - 바뀐 것 없음 → STOP_NO_CHANGES.
7. **추가 권한 표지(올리기만 함)**: 추가된 줄의 `order_authority … true`, 추가된 줄의 `kill_switch`, 지운 줄의 `order_authority`·`kill_switch`. 약 57개 게이트 스크립트를 목록 없이 덮는다.
8. **authority-paths.txt 범위**(2절 표):
   - 불변 조건·노출·주문 모듈의 테스트 파일도 넣었다.
   - 불변 조건 정의 문서 2개도 넣었다.
   - run_auto_core.ps1·register_auto_core_task.ps1은 한도 로직이 없지만 지시문 후보라서 넣었다(진입점·등록 변경 = 승인).
9. **기준 커밋에서 읽기**: Judge 지시(judge-prompt.md)·지시문·builder-rules·authority-paths를 모두 `git show <base>:…`로 읽는다. 메인 작업 트리 파일은 쓰지 않는다. 메인에 커밋 안 된 수정이 있어도 판정 자료가 바뀌지 않는다("메인의 judge-prompt.md" = 메인 base 커밋본).
10. **프로세스 실행 방식**:
    - PowerShell은 claude·python을 `cmd /d /s /c "… > out 2> err"`(Process API, CreateNoWindow)로 실행한다. 바이트를 그대로 두고, 시간 초과면 `taskkill /T /F`로 트리를 끝낸다.
    - devpipe.py 안의 git·테스트 실행은 Python subprocess(인자 목록, 출력 바이트 저장)다. 셸·PowerShell 파이프는 쓰지 않는다. task-prompt.md 복사(`git show`)도 여기서 한다.
11. **잠금**: PID + 프로세스 시작 시각(PID 재사용 대비).
    - 읽을 수 없는 잠금은 120초 동안 살아 있는 것으로 본다.
    - dev-queue는 잠금 주인이 살아 있을 때만 건너뛴다. 죽은 잠금 때문에 큐가 영원히 멈추지 않는다.
12. **시간 상한**:
    - 수정 1회차는 시간도 절반(올림)이다. 지시문은 턴만 절반이라고 했다. 6시간 작업 한도 안에 들기 위해서다: 최악 ≈ 기준선 10 + 120 + 검사 10 + Judge 45 + 60 + 10 + 45 = 300분.
    - Judge 상수: 80턴, 45분. 대상 테스트 30분, 전체 60분, 스키마 10분.
    - dev-queue는 dev-run을 350분에 끊는다(`STOP_QUEUE_TIMEOUT`).
13. **Judge 파싱을 더 엄격히**:
    - `subtype`가 있으면 success여야 한다.
    - json `verdict` = 마지막 줄이어야 한다.
    - PASS인데 `min_fixes`가 비어 있지 않으면 JUDGE_ERROR다(조건부 PASS 금지).
    - Judge 시간 초과 → TIMEOUT(reason judge), 재시도 없음.
    - Judge 뒤 diff_hash를 다시 재서 바뀌었으면 STOP_WORKTREE.
14. **테스트 단계**:
    - ⑥이 실패해도 ⑦까지 돌린다(수정 지시에 정보를 더 넣기 위해서).
    - 대상 패턴이 0개를 돌리면 RETRYABLE(`TARGET_NO_TESTS`).
    - 테스트 시간 초과·`FAILED`인데 실패 id 없음·unexpected success 증가 → RETRYABLE.
15. **dev-merge 세부**:
    - 자기 커밋 뒤 실패하면 커밋을 되돌린다(`reset --soft base` + `reset`, rebase 경우는 먼저 `reset --keep <첫 커밋>`). 같은 run을 다시 병합할 수 있게 하기 위해서다.
    - 기록은 READY인데 다시 계산한 class가 authority면 NEEDS_APPROVAL로 기록하고 멈춘다(exit 3).
    - 이미 병합됨 → STOP_ALREADY_MERGED.
    - `git --literal-pathspecs add --pathspec-from-file`(NUL 구분)을 쓴다. 훅 우회 없음.
16. **창 숨김**: `conhost.exe --headless powershell.exe -WindowStyle Hidden …`. 실행은 확인했다(exit 0, 파일 기록). conhost가 없으면 `powershell -WindowStyle Hidden`이고 깜빡임이 남는다.
17. **메인 체크아웃 검사**: dev-run preflight와 dev-merge는 worktree 사본에서 실행되면 거절한다(`NOT_MAIN_CHECKOUT`).
18. **preflight 보고**: 독립 검사를 모두 돌려 `workspace/outputs/dev-runs/_preflight/<id>.json`에 쓴다. 콘솔 한 줄에는 첫 실패, claude 버전, 플래그 수가 나온다.
19. **결과 기록**:
    - `diff_hash`·`judge_file_sha256`은 READY/NEEDS_APPROVAL 때만 채운다.
    - docs 요약과 `_pending`은 모든 최종 상태(실패 포함)에 쓴다. 23:30에 커밋되므로 Cowork가 결과를 읽을 수 있다.
20. **P9 편집 방식**: 배열 맨 앞에 끼워 순수 추가(+12/−0)로 만들었다. Bash 스크립트로 쓰려던 첫 시도는 auto-mode 분류기가 거절했다. 그 뒤 Edit 도구로 같은 내용을 넣었다.
21. **P5 추가 거절 조건**:
    - 빠진 키.
    - `target_tests`가 `^test[A-Za-z0-9_*-]*\.py$` 밖.
    - allowed_paths 문자가 `[A-Za-z0-9_./-]` 밖.
    - `commit_message`가 ASCII 출력 가능 문자 200자 초과.
22. **commit-docs.ps1 무변경**: run-docs-commit은 그것을 별도 powershell 프로세스로 부른다(git stderr가 PowerShell 오류로 바뀌지 않게). 로그의 비ASCII 바이트는 `?`로 바꾼다.

## 4. 사람이 할 일 (각 한 줄)

- 병합: T3 Judge PASS 뒤 Cowork가 주는 병합 명령 1줄. 이 worktree 변경을 커밋한 뒤 메인(`codex/master-recovery-expansion`, 현재 d7d5292)에서 `git merge --ff-only worktree-redesign-t3`.
- 작업 등록: `powershell -ExecutionPolicy Bypass -File tools\register-dev-tasks.ps1` (메인 체크아웃에서 1번).

## 5. 남는 위험 · 확인 필요

- **헤드리스 실제 실행은 병합 뒤 첫 시험에서만 확인된다.** 확인할 것:
  - `claude -p --worktree`가 만드는 경로·브랜치.
  - CLI json의 `is_error`·`subtype` 존재. 없으면 모든 Judge가 JUDGE_ERROR로 끝난다 → 파서 상수 1곳 수정(기존 방식).
  - acceptEdits + `--permission-prompts none` + `--setting-sources project`가 실제로 allowedTools만 허용하는지.
  - `--tools`에 PowerShell을 적은 것이 Git Bash 환경에서 문제 없는지.
  - 작업 스케줄러(Interactive)에서 claude 로그인·PATH.
- `--max-turns`는 문서 + 파서 검사에 기댄다. 다음 버전에서 사라지면 preflight가 `CLI_FLAG_MISSING`으로 멈춘다(fail-closed).
- Claude Code가 worktree 안에 다른 파일(예: `.claude/` 아래)을 쓰면 STOP_PROTECTED 오탐이 난다. 경로가 결과에 남는다.
- 복사 파일 경합: Builder 시작 직전 스냅샷과 Claude Code의 복사 사이에 메인 `portfolio_state.json`이 바뀌면(예: 06:15 auto-core) STOP_PROTECTED(fail-closed). 새 id로 다시 큐에 넣으면 된다.
- **테스트 실행 = Builder가 쓴 코드 실행**:
  - `python -m unittest <모듈>`로 Builder가 만든 모듈을 돌릴 수 있다. `git diff --output=`도 파일을 쓸 수 있다.
  - 저장소 파일 변화는 ③④가 잡지만, 저장소 밖 부수효과(예: Python 코드가 kiwoomcli를 부름)는 사후 검사로 막지 못한다. 키움 MCP는 `--strict-mcp-config`·`mcp__*` 차단으로 싣지 않는다.
  - 남는 위험이다. 규칙·Judge G3가 보완한다.
- P9 deny·ask는 명령 문자열 매칭이다(문서: 보안 경계 아님). 파이프라인 안의 진짜 경계는 P1 ③(보호 경로)·dev-merge 재검사다.
- `conhost --headless`는 공식 문서화된 옵션이 아니다. 실패하면 로그도 남지 않으므로 `workspace/outputs/dev-runs/_queue/heartbeat.txt` 시각을 본다(15분마다 갱신).
- 병합 실패 경우:
  - dev-merge의 `--ff-only`는 메인 작업 트리의 같은 파일에 커밋 안 된 수정이 있으면 거절된다 → STOP_MERGE_FAILED(되돌림 후).
  - 메인이 docs 외 커밋으로 앞서 가면 STOP_BASE_MOVED → 새 id로 다시.
- 저장소 git 훅이 있으면 dev-merge 커밋에서 돈다(우회하지 않음).
- 23:30 문서 커밋은 메인에 staged 변경이 있으면 멈춘다(commit-docs 기존 동작). 로그: `workspace/outputs/docs-commit/<날짜>.log`.
- CLAUDE.md 문구 반영(4절 4번)은 Cowork 몫이다. 그 전까지 CLAUDE.md의 "tell the user to run tools\commit-docs.ps1" 문장이 남는다.

## r2 (Judge FAIL 수정)

- 지시: `docs/claude/redesign-t3-builder-r2-2026-10-10.md`(1차 Judge FAIL 최소 수정 F1~F3 + 선택 O1·O2·O6).
- BLOCKED 없음. dev-run·dev-merge·dev-queue 실행, 모델을 부르는 `claude -p`, 키움, 비밀 모두 없음.
- `.claude/settings.json` +12/−0, `.gitignore` +2/−0는 1회차 그대로다(이번에 손대지 않음).
- 바뀐 경로는 모두 1회차 허용 경로 안이다. `tools/` 편집은 P9 ask 승인 창을 거쳤다.

### 바꾼 곳 (파일:줄)

- **F1**:
  - `tools/dev-run.ps1:28-38`: `$BuilderAllowedTools`에서 이름만 있는 `Read`·`Edit`·`Write`·`Grep`·`Glob` 5개를 뺐다(이유는 주석). 경로를 묶은 파일 도구 규칙도 넣지 않았다. `--tools` 목록(27줄)은 그대로다.
  - `test_dev_pipeline.py:816` `test_builder_command_constants`: 모든 규칙이 `Bash(…)`/`PowerShell(…)`이고 이름만·경로 묶은 파일 도구 규칙이 없다는 단언.
  - `tools/dev_pipeline/README.md:76` 고정 상수 줄.
- **F2**:
  - `tools/dev-run.ps1:40-45` 새 상수 `$BuilderDisallowedTools` = `mcp__*`, `Bash(git *--output*)`, `PowerShell(git *--output*)`, `Bash(git *--no-index*)`, `PowerShell(git *--no-index*)`.
  - `:242` Builder 명령이 이 목록을 쓴다. Judge 명령(`--disallowedTools "mcp__*"`)은 그대로다.
  - 테스트 `test_dev_pipeline.py:837` `test_builder_denies_git_output_and_no_index`.
- **F3**:
  - a. `tools/dev_pipeline/devpipe.py:97-99` `REMOVED_LINE_MARKERS`에 `quantity_authority`, `execution_quantity`, `watchlist_approved`, `active_universe_approved`, `new_buy_instrument_approved`를 더했다(올리기만).
  - b. `tools/dev_pipeline/authority-paths.txt:60-61`에 `manage-us-stock-strategy/scripts/build_candidate_discovery_proposal.py`, `manage-us-stock-strategy/schemas/candidate-discovery-proposal.schema.json`을 더했다(둘 다 존재 확인, 승인 const·`False` 줄 있음).
  - c. `test_dev_pipeline.py:412` `test_schema_approval_const_change_raises_class`: 5개 표지 각각 `"<표지>": {"const": false}` → `true`면 `REMOVED_LINE:<표지>`, class = authority(subTest 5개).
  - `README.md:56` 표지 목록.
- **O1**:
  - `devpipe.py:1193` `refresh_include_snapshot`, `:1208` `cmd_snapshot_includes`, `:1727` 하위 명령 `snapshot-includes`.
  - `tools/dev-run.ps1:321-324`: Builder 1회차 `Start-Builder` 바로 앞에서 부른다. 실패하면 그 status로 끝난다. 수정 회차는 다시 재지 않는다(같은 스냅샷).
  - init-run 값은 run.json `include_snapshot_init`에 남긴다.
  - 경로 목록은 `include_candidates(repo, base)` 그대로이고 sha256 정확 일치만 본다 → 예외 범위는 같다.
  - `ensure_baseline`은 경로 목록만 쓴다(기준선 = init 값, 병합 rebase 기준선 = 다시 잰 값, 같은 목록). 어긋남이 없다.
  - 테스트 `test_dev_pipeline.py:429` `test_include_snapshot_remeasured_before_builder`: 기준선 뒤 메인 사본이 바뀌면 init 값으로는 STOP이다. 다시 잰 값과 같으면 STOP이 아니다. worktree 사본만 바뀌면 STOP_PROTECTED다.
  - `README.md:52,77`.
- **O2**:
  - `devpipe.py:563-566`: `expected failures` 증가 → `EXPECTED_FAILURES_INCREASED:<뒤>><기준>`(RETRYABLE, unexpected successes 바로 옆). 파싱은 기존 `parse_unittest_output`이 `OK (…, expected failures=N)`의 키를 그대로 읽는다.
  - 테스트 `test_dev_pipeline.py:293` `test_compare_expected_failures_increase`.
- **O6**:
  - `tools/dev-queue.ps1:17-20` `$CommitDocsLimitSeconds = 900`, `$DevRunLimitMinutes = 340`(350에서 낮춤). `:129` commit-docs 상한이 상수를 쓴다.
  - 테스트 `test_dev_pipeline.py:847` `test_queue_limits_fit_task_limit`: `900/60 + 340 + 5 ≤ $queueLimitHours×60 = 360`, 숫자 직접 기입 금지.
  - `README.md:78`.

### F3 d — 5개 표지가 든 비테스트 추적 파일(`git ls-files`, `manage-us-stock-strategy/tests/` 제외)

- authority-paths 안: 29개.
- **밖: 377개**:
  - docs 113.
  - 커밋된 workspace 산출물 98(`workspace/outputs/activation/…` 등).
  - schemas 72.
  - scripts 58.
  - 그 밖의 스킬 파일 9(assets·references).
  - 보호 경로 27(`stock-strategy-system/…`, 파이프라인이 아예 못 고침).
- 표지별(밖): `quantity_authority` 352 · `execution_quantity` 156 · `watchlist_approved` 12 · `new_buy_instrument_approved` 11 · `active_universe_approved` 0.
- 이 파일들은 줄 표지(지운·바꾼 줄)가 덮으므로 목록 추가는 b의 2개만이다.

### 테스트 수치

- 대상 `test_dev_pipeline*.py`: **Ran 86, OK**(1회차 81 + 새 5).
- `test_auto_core*` Ran 89 OK · `test_reconcile_broker_state*` Ran 56 OK · `test_portfolio_exposure_judge_fixes*` Ran 29 OK.
- 전체(test-runner 서브에이전트, `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`; 숫자는 원본 출력에서 devpipe 파서로 직접 셈): `Ran 2670 tests in 315.808s` · `FAILED (failures=19, errors=9, skipped=2)`.
  - 실패 id 28개 = 1회차 기준선과 **같음**(새 실패 0, 고쳐진 것 0).
  - Ran 2584 → 2670(+86), skipped 2 → 2. `evaluate_tests` 결과 `None []`.
- 스키마 감사 `"status": "PASS"`, exit 0.
- tools/*.ps1 6개 PowerShell 파서 오류 0. .ps1 ASCII·CRLF. 바뀐 파일 전부 CRLF(lone LF 0), BOM 없음.

### 남는 위험 (r2)

- **F1**: 이름만 있는 규칙을 뺀 뒤에도 worktree 안 Read·Grep·Glob이 묻지 않고 되는지, Edit·Write가 acceptEdits로 승인되는지는 문서 근거뿐이다. 첫 시험에서 확인한다. 안 되면 Builder가 아무것도 못 고치고 STOP_NO_CHANGES 또는 BLOCKED로 끝난다(fail-closed).
- **F2 부작용 가능성**: 문서에 "Windows + Git Bash에서 Bash deny(범위 규칙, `--disallowedTools` 포함)는 PowerShell 도구를 끈다"는 문장이 있다. 프로젝트 settings에 이미 범위 Bash deny가 있어 상황은 같다. Builder 테스트는 Bash로 돈다. 첫 시험에서 확인한다.
- **F2 범위**: deny는 명령 문자열 매칭이다(문서: 보안 경계 아님).
  - 옵션 약어(예: `--outp=`)나 다른 호출 형태는 못 막을 수 있다.
  - 저장소 안 쓰기는 P1 ③④가 사후에 잡지만, 저장소 밖 쓰기는 못 잡는다.
- **F3 a 오탐**: `quantity_authority`가 352개 파일(대부분 산출물·스키마의 `"quantity_authority": "none"` 줄)에 있다. 그런 줄을 바꾸거나 지우는 일반 변경도 NEEDS_APPROVAL이 되어 사용자 승인이 1번 더 들 수 있다. 올리기만 하므로 안전 쪽이다.
- **O1**: 다시 잰 스냅샷과 Claude Code의 복사 사이 몇 초 경합은 남는다(fail-closed STOP_PROTECTED).
- **O6**: dev-run 내부 상한 합(최악 약 300분)은 340분 안이다.
