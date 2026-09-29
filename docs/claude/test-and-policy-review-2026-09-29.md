# 투자_V2 작업본 테스트 · 정책 변경 점검 (2026-09-29, 3차 갱신 2026-09-30)

위치: 2026-09-30 Claude 프로젝트 문서에서 저장소 `docs/claude/`로 이동
대상: `코덱스저장소` 작업본 (브랜치 `codex/master-recovery-expansion`, HEAD `0026e79` + 미커밋 변경)
방법: 저장소를 건드리지 않도록 사용자 PC의 Linux VM에 복사본을 만들어 실행. CI와 같은 Python 3.13, `unittest discover`, 설치 스킬 미러 재현. `workspace/outputs`는 테스트가 참조하는 폴더만 복사.

## 0. 정정 (1차 보고 오류)
- 1차 보고의 "548개 파일 변경 / CRLF 때문에 `git diff --check` 실패"는 **VM의 Linux git이 `core.autocrlf` 없이 본 착시**였음.
- Windows git 동작(`core.autocrlf=true`)으로 보면 실제 변경은 **수정 44개 + 미추적 76개 항목**이며 CRLF는 정상.
- 일부 증거 artifact가 CRLF 원본 파일의 raw sha256을 참조하므로 **줄바꿈 일괄 변환은 금지**(해시 바인딩 파손 위험).
- VM에서 git 명령 시 반드시 `-c core.autocrlf=true` 사용.

## 1. 사용자 승인 기록
- 2026-09-29: 사용자가 `stock-strategy-system/alert_policy.json`의 두 예외를 명시 승인.
  - `holding_timing_rules.manual_corporate_action_clearance` (APPROVED, MANUAL_EXISTING_HOLDING_ONLY, `reviewed_receipt_sha256: []`)
  - `second_quote_crosscheck.manual_existing_holding_exception` (수동 기존보유 한정, 독립 종가 누락 시 CONDITIONAL_NON_BLOCKING, 충돌 시 기존 정책 유지)
- 파일 내용 변경 없음(작업본에 이미 존재). 승인 범위는 이 두 항목에 한정.

## 2. Cowork에서 수정한 것
1. (K2, 테스트 기대값) `tests/fixtures/decision-record.valid.test-only.json`: `instrument_registry_version` → `2026-09-02-lmt-instrument-registry-v1`
2. (K2, 테스트 기대값) `tests/test_v2_6_7_session_aware_kiwoom_priority.py`: scope_04 기대 티커에 PGR/JPM/CME/V 추가, extended candidate 테스트는 활성화된 4종목을 먼저 제거한 뒤 확장 경로 검증
3. (K0, 2026-09-30) 저장소 루트에 `CLAUDE.md`(39줄), `.claude/settings.json` 신규, `.gitignore`에 `.claude/worktrees/`, `.claude/settings.local.json`, `CLAUDE.local.md`, `graphify-out/` 추가
- 원래 줄바꿈 유지, 운영 정책·코드 변경 없음. 모두 미커밋.

## 3. 현재 테스트 결과 (74개 파일, 약 1,925건)
- 통과 66개 파일. 실패 8개 파일:

| 분류 | 테스트 | 원인 | 필요 조치 |
|---|---|---|---|
| K3 | test_v2_6_7 (2), test_materialize_kiwoom_session_aware_acceptance_candidate (15) | Kiwoom acceptance manifest `f0bab…`가 `run_manual_portfolio_analysis.py`·테스트의 HEAD 해시(`e1e933…`) 잠금. 신규 후보 테스트는 `2994…`를 active로 가정 | 새 acceptance 후보 생성 + Judge + 사용자 승인 (BOUNDARY_RESET) |
| 테스트 설계 | test_k3_session_calendar_coverage_recovery (7) | 09-03 cutoff로 **현재 Production**(09-22 활성화)을 로드 → TEMPORAL_VIOLATION | 고정 fixture 기반으로 전환 (K2) |
| 기존(HEAD) | test_language_contract, test_v2_5_beginner_renderer ui_07 | `portfolio_decision_dashboard.py` 한글 문자열(ASCII 계약 위반, 128→154줄) | 문자열을 `assets/locales/ko-KR.json`으로 이동 (K2) |
| 외부 의존성 | test_portfolio_decision_dashboard (7) — CA clearance 관련 | `bundle_support` 모듈은 저장소 밖 CA successor bundle(`chatgpt md_주식/ca-k3-*/successor-bundle/bundle_support.py`)에 있음. Windows `TMP` 환경변수도 필요 | Windows에서 bundle 경로 설정 후 재확인. 저장소 테스트가 외부 bundle에 의존하는 구조는 개선 후보 |
| 원인 미확정 | test_integrated_authority_snapshot (2) | evidence_grade UNVERIFIED≠GRADE_B | 추가 조사 |
| 환경 | test_nbis_v4 (2) | Windows 키움 런타임 경로 | Windows에서 재확인 |
- CI 스키마 감사 PASS, compileall PASS.

## 4. 정책 파일 실제 변경 (6개)
- `alert_policy.json`: registry 해시 `750a0b…`(canonical과 일치 확인), 위 승인된 두 예외
- `instrument_registry.json`: LMT 추가 (reference_only, 매수 승인 없음)
- `instrument_identity_activation.json`: CME/JPM/PGR/V 추가 (08-29)
- `session_calendar_activation.json`: 2026-08-29.1
- `kiwoom-session-aware-priority-policy.json`: acceptance `f0bab…`, 4종목 추가 (order_authority=false)
- `source_capabilities.json`: acceptance 해시 갱신
- 미추적 `integrated_identity_session_activation.json` (09-22 ACTIVE, MRVL/SOXX 포함, 캘린더 2026-09-03.1~12-31) 및 이를 뒷받침하는 calendar/identity artifact·source bundle이 **git에 없음**.

## 5. 커밋 (2026-09-30 실행, 사용자 승인, push 안 함)
브랜치 `codex/master-recovery-expansion`, 원격 대비 ahead 16 (기존 11 + 신규 5). `core.autocrlf=true`로 커밋해 저장소 blob은 LF.
1. `6558eb9` chore(authority): authority 상태·정책 6개·calendar/identity artifacts·kiwoom provider evidence (37 files)
2. `a5e872a` feat(portfolio): manual analysis·dashboard·renderer·order intent (13 files)
3. `52fb932` feat(authority): integrated authority·Kiwoom acceptance candidate·provenance tooling (35 files)
4. `91cfaf4` docs: CLAUDE.md·.claude/settings.json·.gitignore·개발 검토 절차·references·AGENTS.md (16 files)
5. `8c251f9` test: Kiwoom scope·decision-record 기대값 정렬 (2 files)
- 커밋 제외(로컬 유지): `%SystemDrive%/`, `visualizations/`, 미추적 `workspace/outputs/*` 24개 폴더 (약 256MB; `official-event-intake/` 250MB·672파일, `external-research-intake/` 이미지 3개)

## 6. 원본 지침 폴더 확인 (2026-09-30)
- `E:\사업\##금동한\chatgpt md_주식\`의 md 10개는 업로드된 ZIP과 sha256이 모두 동일.
- 폴더에는 ZIP에 없는 2026-09-28 CA K3 작업물 3개(`ca-k3-boundary-reset-candidate-*`, `ca-k3-boundary-reset-repair-*`, `ca-k3-official-source-observation-candidate-*`)와 `ca-k3-independent-judge-prompt-20260928.md`가 있음. 승인된 CA clearance 예외의 근거 작업으로 보임(내용 미검토).
