# Kiwoom acceptance `f0bab…` 고정 해시 불일치 진단 (2026-09-29, 읽기 전용)

- 대상: `코덱스저장소`, 브랜치 `codex/master-recovery-expansion`, HEAD `5db9c32` (추적 파일 변경 없음, 미추적만 존재)
- manifest: `workspace/research/provider-evidence/kiwoom/2026-08-29/f0bab7101b61…/session-aware-priority-acceptance-pgr-jpm-cme-v-inactive-superseding-candidate.json`
- 방법: 저장소는 읽기만 함. 해시는 저장소 자체 함수(`normalized_text_sha256`, `file_hash`)와 같은 방식으로 재계산. 테스트는 사용자 PC VM의 `$HOME` 복사본에서 Python 3.13.15로 실행(저장소에 파일 생성 없음).
- 선행 문서: `docs/claude/test-and-policy-review-2026-09-29.md`

## 결론 요약

1. **Hot Path(수동 포트폴리오 분석)를 실제로 막지 않는다.** acceptance 검증은 테스트와 후보 생성 도구에서만 호출된다. 막히는 것은 CI(테스트 17건)와 "키움 우선권이 현재 코드 기준으로 검증됐다"는 거버넌스 근거다.
2. manifest가 고정한 항목은 **구현 파일 16 + 권한 바인딩 4 + 원천 증거 9 = 29개**. 실제 불일치는 구현 파일 **2개**(`run_manual_portfolio_analysis.py`, `test_manual_portfolio_analysis.py`)뿐이다.
3. 명시된 K2 3건(ASCII, K3 캘린더 테스트, 외부 bundle)은 **고정 파일을 건드리지 않는다.** 단, 새 acceptance를 만들려면 **고정된 도구 파일 2개를 반드시 고쳐야 한다**(현재 도구가 교착 상태). 원인을 새로 찾은 테스트 실패 1건(integrated snapshot)은 고치는 위치에 따라 고정 테스트 파일을 건드릴 수 있다.
4. 권장: **K2 전부 → 동결 커밋 → (도구 수정 + 새 후보) 한 묶음으로 Judge 1회 → 사용자 승인 → 활성화 1회.**

---

## 1. Hot Path 차단 여부 — 막지 않음

근거(코드 확인):
- 검증 함수 `validate_acceptance`를 호출하는 곳은 `tests/test_v2_6_7_session_aware_kiwoom_priority.py`, `tests/test_materialize_kiwoom_session_aware_acceptance_candidate.py`, 후보 도구 2개뿐이다.
- 수동 분석 경로 `run_manual_preflight`와 그 import 모듈(`integrated_authority_snapshot`, `kiwoom_runtime_bridge`, `session_aware_market_data`, `kiwoom_account_readonly_bridge`, `session_authority`, `portfolio_decision_dashboard` 등)은 acceptance manifest를 읽지 않는다.
- 예약(scheduled) 경로의 `verify_current_provenance`는 정책 파일 해시를 **배포 manifest**와 비교하는 별도 체계라 이번 불일치와 무관하다.
- `test_manual_portfolio_analysis.py`는 복사본에서 115건 통과(1건 skip)했다.

실제 영향:

| 영향 | 내용 |
|---|---|
| CI | `safety-ci.yml`의 `unittest discover`에서 17건 실패(test_v2_6_7 2 + materialize 15) |
| 거버넌스 | `KIWOOM_PRIMARY_GUARDED_SCOPED` 근거가 8/27 코드(`7fa30b0`) 기준. 지금 Hot Path는 acceptance가 다루지 않은 코드로 실행 중이며, 런타임은 이를 차단하거나 등급을 낮추지 않는다(무음) |
| Judge 검토 필요 변경 | `a5e872a`는 기능 추가가 대부분이지만, fail-closed 조건도 바꿨다: `KIWOOM_UNAVAILABLE`은 `oauth_health`를 요청했을 때만 hard fail, 보유내역 미조회는 요청하지 않았으면 hard fail 대신 PARTIAL |

이 상태를 수동 분석 판단(등급 표시 등)에 반영할 규칙은 현재 없음 → **확인 필요**.

## 2. manifest가 고정한 파일 전체 목록

### 2-1. 구현 파일 16개 (`implementation_hashes`, CRLF/BOM 정규화 해시 — 불일치 시 검증 실패)

| # | 파일 (`manage-us-stock-strategy/` 하위) | 현재 | 마지막 일치 커밋 |
|---|---|---|---|
| 1 | schemas/kiwoom-provider-scope.schema.json | 일치 | 52fb932 |
| 2 | schemas/kiwoom-session-aware-acceptance-manifest.schema.json | 일치 | 52fb932 |
| 3 | schemas/kiwoom-session-aware-priority-policy.schema.json | 일치 | 8d604bb |
| 4 | schemas/source-capability.schema.json | 일치 | 944bfde |
| 5 | scripts/build_kiwoom_market_snapshot.py | 일치 | 944bfde |
| 6 | scripts/build_kiwoom_session_observation.py | 일치 | 944bfde |
| 7 | scripts/kiwoom_provider_preflight.py | 일치 | 944bfde |
| 8 | scripts/kiwoom_runtime_bridge.py | 일치 | 7da9df5 |
| 9 | scripts/materialize_kiwoom_session_aware_acceptance_candidate.py | 일치 | 52fb932 |
| 10 | scripts/run_kiwoom_session_aware_validation.py | 일치 | 944bfde |
| 11 | **scripts/run_manual_portfolio_analysis.py** | **불일치** (고정 `E1E933…` / 현재 `BAEC16…`) | 7fa30b0 → a5e872a에서 +1,093줄 |
| 12 | scripts/session_aware_market_data.py | 일치 | 944bfde |
| 13 | scripts/validate_kiwoom_market_snapshot.py | 일치 | 944bfde |
| 14 | scripts/validate_kiwoom_session_aware_acceptance.py | 일치 | bd69815 |
| 15 | scripts/validate_kiwoom_session_aware_acceptance_candidate.py | 일치 | 52fb932 |
| 16 | **tests/test_manual_portfolio_analysis.py** | **불일치** (고정 `366685…` / 현재 `7368D7…`) | 7fa30b0 → a5e872a에서 +969줄 |

복사본에서 `validate_acceptance`를 직접 실행한 결과 오류는 위 2건뿐이었다.

### 2-2. 권한 바인딩 4개 (`authority_bindings`, raw 바이트 해시 — 후보 단계 기록용)

| 이름 | 경로 | 현재 |
|---|---|---|
| active_acceptance_manifest | `workspace/research/provider-evidence/kiwoom/2026-08-26/…-675a7ee-inactive-candidate.json` (`2994…`) | 일치 |
| active_priority_policy | `workspace/policies/kiwoom-session-aware-priority-policy.json` | 다름(예상됨) |
| provider_scope_policy | `workspace/research/provider-evidence/kiwoom/2026-08-28/…-superseding-candidate.json` | 일치 |
| source_registry | `workspace/policies/source_capabilities.json` | 다름(예상됨) |

"다름(예상됨)" 2개는 활성화 때 정책이 `f0bab…`를 가리키도록 바뀌었기 때문이다. 운영 검증 함수는 이 raw 해시를 보지 않는다.

### 2-3. 원천 증거 9개 (`source_artifacts`, raw 해시 — 파일이 있을 때만 검사)

모두 `workspace/outputs/activation/…`(git 미추적)에 있고 9개 모두 일치: active_provider_smoke, candidate_primary_replay, extended_hours_snapshot, fault_injection, finalized_regular_validation, five_session_acceptance, latest_kiwoom_daily_snapshot, latest_yfinance_shadow, session_aware_validation.

### 2-4. 이 manifest 해시를 가리키는 쪽 (새 acceptance 활성화 때 같이 바뀜)

- `workspace/policies/kiwoom-session-aware-priority-policy.json`: `provider_scopes` 15행의 `acceptance_artifact_hash` + `acceptance_evidence.session_aware_acceptance_manifest_sha256`
- `workspace/policies/source_capabilities.json`: `kiwoom_rest.acceptance_artifact_sha256`

## 3. 남은 K2 수정과 고정 파일 교차

| 수정 | 바꿔야 할 파일 | f0bab 고정 파일? | 주의 |
|---|---|---|---|
| ASCII 규칙 | `scripts/portfolio_decision_dashboard.py`(154줄), **`scripts/sec_official_event_intake.py`(109줄)**, **`scripts/verify_kiwoom_spec_mcp.py`(3줄)** + 새 locale 파일 | 아니오 | 선행 문서는 dashboard만 적었으나 실제 위반은 3개 파일(테스트가 첫 실패 파일에서 멈춰 가려져 있었음). dashboard·intake의 한글은 화면 문구 → locale 이동. `verify_kiwoom_spec_mcp.py`의 3줄은 키움 API 이름(데이터) → `\uXXXX` 이스케이프가 더 안전. `assets/locales/ko-KR.json`은 `alert_policy.json` 배포 게이트가 해시(`5A0F54…`)로 고정 → 여기에 추가하면 승인 정책 수정이 필요. **별도 파일**(선례: `save-daily-ko-KR.json`)로 분리 권장 |
| K3 캘린더 테스트 | `tests/test_k3_session_calendar_coverage_recovery.py` (+ fixture) | 아니오 | `load_production_…`이 현재 Production(09-22)을 읽어 `TEMPORAL_VIOLATION`(7건 재현). 09-03 manifest를 명시 경로로 읽도록 바꾸면 테스트가 증명하는 내용이 달라지므로 Judge가 의미를 확인 |
| 외부 bundle 의존 | `tests/test_portfolio_decision_dashboard.py` (+ 테스트 helper) | 아니오 | `bundle_support.py`는 외부 폴더에 **서로 다른 3개 버전**이 있고 `E:\…\코덱스저장소` 경로를 하드코딩. 어느 버전을 쓰느냐에 따라 결과가 달라짐 |
| (추가) integrated snapshot 2건 | 원인은 테스트 픽스처. 픽스처 helper `market_reader_for`는 **고정 파일** `tests/test_manual_portfolio_analysis.py`에 있음 | **helper를 고치면 예 / 로컬 보정이면 아니오** | ① 페이지 `retrieved_at`이 `2026-08-21T22:00Z`(장 마감 이전) → `LOCAL_BAR_PAGE_BINDING_INVALID`. ② 이를 보정해도 일봉 행이 `normalize_series`에서 `COMPLETED_SESSION_MISSING`·`INSUFFICIENT_HISTORY`로 막힘(행 형식 세부는 확인 필요). 운영 코드 결함 근거는 못 찾음. **고정 안 된 `test_integrated_authority_snapshot.py` 안에서 자체 일봉 응답을 만드는 쪽 권장** |
| (추가) acceptance 도구 | `scripts/materialize_…_candidate.py`, `scripts/validate_…_candidate.py`(둘 다 **고정**), `tests/test_materialize_…py`(비고정) | **예** | 아래 교착 참고 |

**새 acceptance 생성이 현재 막혀 있는 이유 (교착):**
- 후보 생성 도구는 "현재 활성 acceptance가 유효해야" 후보를 만든다. 그런데 활성 `f0bab…`는 구현 해시 불일치로 무효 → 도구가 `current active Acceptance invalid`로 거부한다(테스트 14건 오류의 원인).
- 도구는 "활성 11종목 → 15종목 확장" 1회용으로 하드코딩돼 있다(`ACTIVE_PROVIDER_SCOPE` 11개). 지금은 15종목이 활성이라 `active 11-symbol provider scope changed`로도 거부된다.
- 테스트는 활성 manifest를 `2994…`(08-26) 경로로 하드코딩했다.
- 결론: 새 acceptance를 만들려면 **고정된 도구 2개 수정이 먼저**다. 특히 "활성 acceptance가 무효여도 후속 후보를 허용"하는 부분은 fail-closed 조건을 완화하는 것이라 **K3**다.

## 4. 권장 순서 — K2 먼저, 새 acceptance는 한 번만 고정

| 단계 | 내용 | 등급·위치 | 통과 조건 |
|---|---|---|---|
| 0 | 이 진단 (완료) | 읽기 전용 | — |
| 1 | ASCII 3개 파일 → 새 locale 파일 분리 (`ko-KR.json`·`alert_policy.json`은 건드리지 않음) | K2, Claude Code 새 worktree | language_contract·beginner_renderer 통과 + dashboard md/html 출력 바이트가 수정 전과 동일 |
| 2 | K3 캘린더 테스트를 09-03 manifest 명시 로드로 전환 | K2(테스트) | 7건 통과. 현재 Production이 09-22 cohort라는 별도 단언 유지 |
| 3 | 외부 bundle 제거: 필요한 `technical_projection`만 테스트 helper로 저장소에 옮기고 출처 파일·sha256 기록 | K2(테스트) | 외부 폴더·Windows `TMP` 없이 통과 |
| 4 | integrated snapshot 2건: `test_integrated_authority_snapshot.py` 안에서 픽스처 보정(고정 helper는 건드리지 않음). 부득이 helper를 고친다면 반드시 이 단계에서 | K2(테스트). 운영 코드 수정이 필요해지면 K3로 격상 | 2건 통과 + `test_manual_portfolio_analysis` 115건 유지 |
| 5 | **동결**: 고정 16개 파일 중 1~4에서 바뀐 것이 있는지 확인 → 사용자 승인 후 커밋. 이후 고정 파일 수정 금지 | 커밋(사용자 승인) | acceptance 관련 17건 외 전체 통과 |
| 6 | 도구 수정: 구현 드리프트만 있는 경우 후속 후보를 허용하되, 바뀐 파일·이전/현재 해시를 후보에 기록. 스코프는 활성 정책에서 읽기(동일 15종목 재승인). 테스트는 활성 manifest를 정책에서 찾도록 변경 | **K3, BOUNDARY_RESET**, Claude Code 새 worktree | materialize 테스트 통과 |
| 7 | 6 커밋 기준으로 새 INACTIVE 후보 1회 생성 → 후보 검증기 PASS | K3 | 후보 파일 1개 + 해시 |
| 8 | 독립 Judge 1회: 6·7 + `a5e872a`의 fail-closed 변경 + 08-13/14 증거 재사용 적정성 | K3, 별도 Claude Code 세션 | Judge PASS |
| 9 | 사용자 승인 후 활성화: 정책 15행 + `acceptance_evidence` + `source_capabilities` 해시 교체 | K3, 승인된 정책 수정 | 전체 테스트 통과(Windows 전용 제외) |

순서가 이런 이유: 6단계 도구 파일도 고정 대상이다. 7단계 이전에 고정 파일이 하나라도 더 바뀌면 새 acceptance가 다시 깨진다. 그래서 고정 파일을 건드릴 수 있는 작업(4, 6)을 모두 7 앞에 둔다.

## 5. 사용자 결정 필요

1. 위 계획 실행 승인 (단계별로 끊어서 승인해도 됨)
2. 새 acceptance 증거: 08-13/14 증거 재사용(재승인)인지, 새 실시간 키움 조회 증거를 요구할지 — 권장: 재사용 + Judge가 `a5e872a`의 의미 변경이 기존 증거로 충분히 뒷받침되는지 판정
3. (나중 검토 후보) `run_manual_portfolio_analysis.py`를 고정 목록에서 뺄지. Hot Path 파일이라 고칠 때마다 K3가 된다. 다만 이는 거버넌스 변경(K3)이므로 이번에는 **현행 유지(NO_CHANGE)**를 권장

## 승인 기록

- 2026-09-29: 사용자가 **1~5단계만** 승인(K2 수정 4건 + 동결 커밋). 6~9단계(K3)는 별도 승인 필요. 고정 16개 파일은 이 범위에서 수정 금지.

## 진행 기록

- 2026-09-29 **1단계 완료** (worktree `.claude/worktrees/k2-pin-safe-fixes`, 미커밋): 스크립트 3개 수정 + 새 locale 2개(`portfolio-decision-dashboard-ko-KR.json` 키 183, `sec-official-event-intake-ko-KR.json` 키 133). 고정 16개·`ko-KR.json`·`alert_policy.json` 미변경.
- Cowork 독립 확인(main 바이트 복사본 + 1단계 변경 적용): `scripts/*.py` 전부 ASCII. language_contract 2건, beginner_renderer 43건, sec_official_event_intake 41건 통과. dashboard 306건 중 실패 8건은 수정 전과 **동일한 목록**(bundle_support 없음 6, `TMP` 1, 미추적 fixture 1).
- 1단계 보완 필요: 옮긴 문구 파일이 출력 기록(provenance)에 빠짐 → dashboard `implementation_provenance_paths`, sec intake `implementation_hashes`에 추가. `deployment_provenance.py`의 필수 경로는 이번에 건드리지 않음(예약 실행 배포 manifest에 영향).
- 발견: worktree는 새 체크아웃이라 줄바꿈이 CRLF로 바뀌어, 원시 해시로 묶인 증거 파일이 main과 다름(예: identity artifact `d8b03aa4…`→`b9041bc8…`, acceptance manifest `f0bab…`→`0a7de90c…`). `workspace/`·`stock-strategy-system/` 추적 파일 343개 중 201개는 main 바이트와 git blob이 다름 → 어떤 체크아웃으로도 main 바이트를 재현할 수 없음. 그래서 원시 해시를 검사하는 테스트(2·4단계 대상 포함)는 worktree에서 판정 불가 → **2~4단계는 main 폴더에서 진행**, 5단계에서 worktree 변경을 합침.
- 범위 밖 과제 후보: 새 clone이나 CI(LF 체크아웃)에서 원시 해시 증거가 재현되지 않을 가능성 — 확인 필요.
- 2026-09-29 **1단계 보완 완료**: dashboard `implementation_provenance_paths`에 `DASHBOARD_TEXT_PATH`, sec intake `implementation_hashes`에 locale 해시 추가. Cowork 재확인: language_contract·sec intake 통과, dashboard 실패 목록 수정 전과 동일.
- 2단계 준비 확인: 09-03 manifest(`8a23e784…`, CRLF)는 git에 없고 미추적 `workspace/outputs/k3-session-calendar-coverage-recovery/20260903T144025Z/`에만 있음 → 테스트 fixture로 바이트 그대로 복사 필요. 복사본으로 모의 실행 시 캘린더 테스트 전부 통과.
- 2026-09-30 **2단계 완료** (원본 폴더, 미커밋): 09-03 manifest를 `tests/fixtures/k3/integrated_identity_session_activation.20260903.json`으로 바이트 그대로 복사(sha256 `8a23e784…` 일치), `test_k3_session_calendar_coverage_recovery.py`가 fixture를 읽도록 변경 + 현재 Production 로드 확인 테스트 1개 추가. Cowork 확인: 6건 통과.
- 2026-09-30 **3단계 완료** (원본 폴더, 미커밋): 외부 `bundle_support.py` 대신 테스트 전용 `tests/ca_projection_support.py` 사용(`technical_projection`·`timestamp`만, 외부 3개 버전과 AST 동일 — Cowork 재확인, 원본 경로·sha256 주석 기록). `os.environ["TMP"]` → `tempfile.gettempdir()`. Cowork 확인(1단계 변경 합친 상태): dashboard 306건 중 실패 1건 — 미추적 fixture `workspace/outputs/manual-portfolio-analysis/manual-20260829T153208101909Z-…` 부재(복사본 한정, 원본 폴더에는 존재). integrated snapshot 2건은 4단계 대상으로 그대로.
- 2026-09-30 **4단계 완료** (원본 폴더, 미커밋): `test_integrated_authority_snapshot.py` setUp 안에서만 PGR 일봉 픽스처 보정(OHLCV 채움, 페이지 retrieved_at). 고정 파일 `test_manual_portfolio_analysis.py` 미변경(115건 통과 유지). 2건 중 1건 해결.
- 남은 1건(`test_downstream_handoff_dashboard_and_sidecar_use_same_validator`)은 **테스트 기대값 모순**: 방향 전용 증거는 `validate_manual_direction_evidence`가 `finalized_bar_preflight_status == "FAIL"`을 요구하므로 대시보드 gate에 `FINALIZED_BAR_NOT_VERIFIED`·`FINALIZED_BAR_PREFLIGHT_NOT_PASS` 두 개가 항상 남음. 대시보드 `_manual_local_timing_gate`가 정확히 이 두 개만 허용하도록 설계돼 있고, 같은 입력에서 sidecar `manual_grade_b_eligible`=True, 등급 GRADE_B. 1단계 대시보드 변경과 무관(원본 dashboard로도 동일). → 기대값을 두 blocker로 바꾸는 테스트 수정 권장(런타임 변경 없음). Judge(8단계)가 이 의미 해석을 재확인.
- 2026-09-30 **4단계 보완 완료**: 기대값을 두 finalized-bar blocker로 변경. Cowork 확인: `test_integrated_authority_snapshot` 38건 전부 통과.
- 2026-09-30 **5단계 시작(합치기, 미커밋)**: worktree의 1단계 파일 5개(스크립트 3 + locale 2)를 원본 폴더로 복사. worktree 사본의 CRLF는 체크아웃 부산물이므로 원본 폴더의 기존 LF 형식으로 맞춤(정규화 해시 동일 확인). 원본 폴더 기준 scripts 전부 ASCII, 고정 16개 중 불일치는 기존 2개 그대로(새로 깨진 것 없음).
- 참고: 예약 자동화(Codex `post-close-portfolio-strategy`, Pre-Open)는 별도 런타임 clone `E:\사업\##금동한\runtime\stock-strategy-scheduled`의 고정 HEAD `41f7b3f…`에서 실행 → 이 저장소 커밋은 예약 실행에 즉시 영향 없음. manifest의 `official_runtime_commit 69642586…`도 그 런타임 쪽 커밋일 가능성(확인 필요).
- 2026-09-30 **5단계-1 전체 테스트(Windows 원본 폴더)**: 1,897건 중 실패 23건(`docs/claude/test-run-latest.md`). 예상된 acceptance 17건(materialize 15, v2_6_7 2) + 예상 밖 6건. 스키마 감사 PASS.
  - 예상 밖 6건은 이번 변경과 무관하다고 판단(코드 경로 근거): `test_sec_scheduled_shadow` 01·05·23은 Python을 호출하지 않는 `register_sec_scheduled_shadow_task.ps1`(08-31 이후 미변경)의 PowerShell `Join-Path` 오류, 35·37은 임시 폴더에 **가짜** intake 스크립트를 써서 실행하므로 실제 `sec_official_event_intake.py`를 쓰지 않음. `test_save_daily_pipeline`은 Windows Python에 `pypdf` 미설치. 변경 전 Windows 기준 실행으로 직접 대조하지는 않음(확인 필요 수준은 낮음).
  - 후속 과제 후보(범위 밖): PowerShell 테스트의 Windows 호환(5건), `pypdf` 설치 또는 테스트 skip 처리.
- 2026-09-30 **5단계 커밋 완료** (사용자 승인, push 안 함, 브랜치 `codex/master-recovery-expansion`): `4db8c51` refactor(i18n) 한글 문구 분리(5 files) · `9b54097` test 자립화(5 files) · 이 문서와 `test-run-latest.md`는 docs 커밋. 고정 16개 파일은 이 커밋들에 포함되지 않음 → **동결 상태**. 이후 고정 파일 수정은 6단계(K3)에서만.
- VM에서 커밋 시 git이 잠금·임시 파일(`.git/HEAD.lock`, `index.lock`, `maintenance.lock`, `tmp_obj_*`)을 지우지 못해 남김 → 사용자 삭제 허용 후 정리. 이후 VM의 git 조회는 반드시 `--no-optional-locks` 사용.
- worktree `.claude/worktrees/k2-pin-safe-fixes`의 1단계 변경은 이제 커밋에 들어갔으므로 worktree는 정리 대상(미커밋 사본만 남음).
- 참고: 커밋된 09-03 fixture는 git 안에서 LF로 저장됨. Windows(autocrlf=true) 체크아웃에서는 원래 바이트(`8a23e784…`)로 복원되나, LF 체크아웃(Linux CI)에서는 해시가 달라짐 → 기존 원시 해시 재현성 과제와 같은 부류.

## 6. 미검증 / 확인 필요

- manifest의 `official_runtime_commit` `69642586…`는 이 저장소에 없다(`repository_base_commit` `10569ee`는 있음). 확인 필요
- `sec_official_event_intake.py` 한글 109줄 중 앞·뒤 일부만 확인(화면 문구·HTML). 전체가 문구인지는 수정 시 확인 필요
- integrated snapshot 픽스처의 일봉 행이 `normalize_series`를 통과하지 못하는 정확한 필드 원인은 확인 필요
- Windows 전용 실패(`test_nbis_v4`, dashboard의 `TMP`)는 이번 범위 밖
- 설치 스킬 사본(`.codex/skills/manage-us-stock-strategy`)에는 `run_manual_portfolio_analysis.py`가 없다. 수동 분석은 저장소에서 직접 실행되는 것으로 보이나 실제 실행 명령은 확인 필요
