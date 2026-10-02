# S7 달력 연결 Builder 지시문 — S7 계산이 Production 통합 권한의 달력을 읽게 하기 (2026-10-02, K2 + Judge)

- 목적: S7 1차 코드(`run_portfolio_exposure_review.py`, `regular_session_close_history.py`)가 옛 단독 달력 파일 대신 **Production 통합 권한**(`workspace/policies/integrated_identity_session_activation.json`)에서 세션 달력을 읽게 한다. 수동 분석·대시보드·주문의도 모듈이 이미 쓰는 그 권한이다.
- 배경: S7 Builder 보고 F1·U1("ACTIVE 달력은 2026-08-29까지, 9월 이후 달력 활성화는 별도 K3")은 옛 파일 `workspace/policies/session_calendar_activation.json`만 보고 내린 판단이었다. 실제로 2026 전체 달력 `2421eeb7…`은 9/3 K3(Session Calendar Coverage Recovery)부터 통합 권한에서 ACTIVE 상태다. 그래서 **새 달력을 활성화할 필요는 없고**, 바꿀 것은 S7 코드가 어느 권한 파일을 읽느냐뿐이다.
- 사용자 결정(2026-10-02): 선택 A "통합 권한 연결"(정책 파일 무변경). 선택 B(옛 파일을 `2421eeb7…`로 갱신)는 택하지 않음.
- 성격: K2(런타임 계약). 권한 연결을 바꾸는 일이라 별도 Judge를 받는다. 정책·권한 원본·상태 파일은 바꾸지 않는다. `order_authority=false`, `quantity_authority=none`, `execution_quantity=null` 유지.
- 상태: 작성 완료, Builder 미실행.

## 1. 사용자 조작 (Windows 터미널)

**[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: high · 세션: 새 worktree `s7-cal-bind` · 이유: 설계는 확정됨, 스크립트 2개와 테스트만 고치는 K2 작업(Judge는 Opus xhigh로 따로 진행)**

1. 새 Windows 터미널에서 다음을 입력한다: `cd "E:\사업\##금동한\코덱스저장소"`
2. 이 지시문을 커밋한다(worktree는 커밋된 HEAD에서 만들어진다).
   `git add docs/claude/s7-calendar-binding-builder-prompt-2026-10-02.md`
   `git commit -m "docs: S7 calendar binding builder prompt"`
3. `claude --worktree s7-cal-bind`를 입력한다.
4. 세션 안에서 `/model`로 Sonnet을, `/effort`로 high를 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `docs/claude/s7-calendar-binding-builder-prompt-2026-10-02.md 3절 상자 안의 지시를 그대로 따르는 Builder로 일해라. 그 밖의 절은 참고만 한다.`
6. 권한 확인 창
   - 허용: 파일 읽기, `git status`/`log`/`diff`/`show`, python 테스트·해시 계산, worktree 안 파일 쓰기.
   - 거부: 키움 도구 전부, `.env` 읽기, worktree 밖 파일 쓰기, `reconcile_broker_state.py apply`, `portfolio_review_journal.py apply`, 커밋·push·merge.
7. Builder가 1단계 정지점에서 멈추면 Cowork에 "달력 Builder 정지 1단계"만 보낸다.
8. 끝나면 Cowork에 "Builder 완료, worktree s7-cal-bind, 새 실패 수 N"만 보낸다. 그다음 Judge와 커밋·병합은 Cowork가 안내한다.

## 2. Cowork 사전 확인 (2026-10-02, 원본 폴더 읽기 전용, Builder가 다시 확인)

| # | 사실 | 근거 |
|---|---|---|
| C1 | 통합 권한 원시 sha256은 `c5ee680d…`, ACTIVE이며 cohort는 `identity-confirmation-approved-20260922T234229Z`(activated_at `2026-09-22T23:42:29Z`)다. 세션 달력은 `2421eeb7e115ad640b6b0ec76d0d88cfe2a49499c12c39dc35ea5f71c1fed22b`(버전 `2026-09-03.1`, 2026-01-01~2026-12-31, 251세션)다 | `workspace/policies/integrated_identity_session_activation.json` |
| C2 | 검증기 결과 **PASS**: 대상 세션 2026-10-01 REGULAR(`core_close_at 2026-10-01T16:00:00-04:00`), SOXL은 신원·세션 모두 VERIFIED, 해시 일치 | `validate_integrated_authority_production.py --decision-as-of 2026-10-02T09:00:00+09:00 … --target-session-date 2026-10-01 --ticker SOXL`(출력 파일 없이) |
| C3 | 옛 파일 원시 sha256은 `ae67d222…`이고 달력 `d6d1ecd…`(2026-08-29까지)를 가리킨다. 통합 로더는 이 파일을 읽지 않는다("no legacy fallback") | `integrated_authority_snapshot.py:306-322` |
| C4 | 옛 파일 해시와 파일 이름은 키움 acceptance(`workspace/research`), 정책, 상태 어디에도 고정돼 있지 않다 | grep |
| C5 | 옛 파일을 읽는 S7 코드는 2곳이다: `run_portfolio_exposure_review.py:49`(`DEFAULT_ACTIVATION`), `:291-299`(`resolve_calendar_path`), `:339-341` / `regular_session_close_history.py:38`, `:71-94`(`load_calendar`), `:318` | 원본 |
| C6 | 두 스크립트는 S7에서 새로 만든 파일이라 고정 파일 22개(배포 6 + acceptance 16)에 들지 않는다. 원본 폴더 기준 CRLF다 | S7 보고 4.5, 줄바꿈 확인 |
| C7 | 이력 파일 스키마 `regular-session-close-history.schema.json`의 `calendar` 블록은 `additionalProperties: false`이고 `authority_status`는 `ACTIVE`·`EXPLICIT_ARTIFACT_NOT_ACTIVE` 두 값만 허용한다. 실행 결과의 `inputs`는 자유 object다 | 스키마 |
| C8 | 통합 로더 `load_production_integrated_authority_snapshot(trusted_root, decision_as_of, resolved_at, run_id)`는 `snapshot.session.artifact`, `snapshot.session.calendar_hash`, `snapshot.provenance(authority_source=…)`를 준다. 실패하면 `IntegratedAuthorityLoadError.reason`(`ARTIFACT_NOT_ACTIVATED` / `INTEGRITY_FAILURE` / `TEMPORAL_VIOLATION`)를 낸다 | `integrated_authority_snapshot.py:57-93, 232-322` |
| C9 | worktree는 CRLF로 체크아웃된다. 그래서 실제 달력·통합 권한 파일의 원시 해시가 맞지 않아 worktree 안에서는 실제 권한이 로드되지 않는다(S7-1 Judge 기록과 같음). 테스트는 임시 trusted root에 git blob 바이트(`git show HEAD:<path>`)나 기존 헬퍼(`tests/test_integrated_authority_snapshot.py` `_copy_artifacts`·`_active_manifest`)로 만든 픽스처를 쓴다. 실제 자료 확인은 병합 뒤 Cowork가 원본 폴더에서 한다 | S7-1 Judge 참고 |

## 3. Builder 지시 (이 상자만 따른다)

```
역할: 투자_V2 Builder (K2 + 별도 Judge). 범위 = S7 스크립트 2개가 세션 달력 권한을 Production 통합 권한에서 읽도록 바꾸기.
주문·수량 권한 없음. 키움 도구 호출 금지. 비밀(.env*, 토큰, 계좌번호) 읽기 금지.

바꿔도 되는 파일(이것만):
- manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py
- manage-us-stock-strategy/scripts/regular_session_close_history.py
- manage-us-stock-strategy/tests/test_run_portfolio_exposure_review.py (픽스처 연결만)
- manage-us-stock-strategy/tests/test_regular_session_close_history.py (달력 권한 테스트만)
- manage-us-stock-strategy/tests/test_portfolio_exposure_judge_fixes.py (달력 픽스처 연결이 필요할 때만)
- 새 파일 manage-us-stock-strategy/tests/test_s7_calendar_binding.py
- 새 파일 docs/claude/s7-calendar-binding-builder-report-2026-10-02.md (보고)
그 밖의 파일은 고치지 않는다. 특히 workspace/policies/* (두 activation 파일 포함), integrated_authority_snapshot.py,
session_authority.py, session_calendar_artifact.py, 스키마, alert_policy.json, 상태·원장·journal, 고정 파일 22개.
이 목록 밖을 바꿔야 하면 멈추고 묻는다.

요구:
R1 권한 출처: 두 스크립트의 달력 권한은 load_production_integrated_authority_snapshot 하나만 쓴다.
   옛 session_calendar_activation.json 읽기와 DEFAULT_ACTIVATION, resolve_calendar_path의 activation 읽기를 없앤다.
   "ACTIVE" = 로더 성공 AND 쓰는 달력 artifact의 원시 sha256 == snapshot.session.calendar_hash.
R2 바꿔 끼우기 금지 유지: 권한 파일·trusted root를 바꾸는 명령 인자·환경변수를 만들지 않는다(S7 보고 3.5-4 규칙).
   테스트용 seam은 지금처럼 모듈 상수(예: 신뢰 루트 상수)를 테스트가 mock.patch로 바꾸는 방식만 쓴다.
R3 실패 처리(fail-closed):
   - 실행기: 로더 실패 → ReviewRunError("SESSION_CALENDAR_UNAVAILABLE:<reason>"), 결과 파일 없음(지금 실패 경로와 같게).
     --calendar로 다른 artifact를 주면 지금처럼 EXPLICIT_ARTIFACT_NOT_ACTIVE(종가 미확인).
   - 이력 빌더: --calendar artifact는 그대로 받는다. 로더 실패나 해시 불일치면 EXPLICIT_ARTIFACT_NOT_ACTIVE(종가 미확인).
     이력 파일 calendar 블록 키와 상태 값은 바꾸지 않는다(스키마 C7). 실패 사유는 CLI 출력 JSON에만 더한다.
   - 실행기는 이력 파일에 적힌 authority_status를 믿지 않고 지금처럼 다시 판정한다.
R4 시점: decision_as_of = 실행 시각(실행기는 current_time() 또는 --now 값, 이력 빌더는 현재 UTC).
   resolved_at도 같은 값. activated_at보다 이른 시각이면 로더의 TEMPORAL_VIOLATION을 그대로 실패로 둔다.
R5 출처 기록: 실행 결과 inputs에 새 키 calendar_authority를 더한다(snapshot.provenance(authority_source="K3_COMBINED_PRODUCTION")
   중 combined_activation_manifest_sha256, activation_cohort_id, session_calendar_artifact_sha256, session_calendar_version).
   inputs.calendar(기존 identity) 키 구성은 그대로 둔다.
R6 문구: run_portfolio_exposure_review.py의 "ACTIVE calendar ends 2026-08-29" 주석처럼 옛 사실을 적은 주석·도움말을 고친다.
R7 줄바꿈: 각 파일의 기존 줄바꿈·BOM을 유지한다. 일괄 변환 금지.

단계:
0. 기준선: git status, HEAD(이 지시문 커밋이어야 함, 아니면 멈춤), 바꿀 파일 5개의 원시 sha256을 기록한다.
   전체 테스트를 서브에이전트로 1회 돌린다(실패 ID만 파일로 저장):
   python -m unittest discover -s manage-us-stock-strategy/tests
   보고 파일 0절에 실패·오류 수와 목록 파일 sha256을 적는다.
1. 조사(읽기만) → 보고 1절 → 멈춘다. file:line 근거로 다음을 적는다:
   a. 두 스크립트에서 바꿀 곳과 바꾼 뒤의 호출 흐름
   b. 기존 테스트 중 옛 activation 파일에 기대는 것과 각 단언의 뜻(바꾼 뒤에도 같은 뜻을 지키는 방법)
   c. 통합 로더 픽스처를 만드는 방법(C9), CRLF 영향
   d. R1~R7 가운데 코드 현실과 충돌하는 것(있으면 대안을 1개만 제안)
   여기서 사용자가 "진행"이라고 할 때까지 멈춘다.
2. 테스트 먼저: test_s7_calendar_binding.py를 쓰고, 고치기 전 코드에서 실패하는지 확인한다(보고에 수 기록).
   T1 기본 실행: 유효한 통합 권한(임시 root) → 달력 ACTIVE, 평가 세션 = 시계 기준 최근 완료 세션, inputs.calendar_authority 기록
   T2 옛 파일 무시: 옛 activation 파일이 다른 artifact를 ACTIVE로 적거나 없어도 결과가 같다
   T3 실패: 통합 권한 없음 / SHADOW / 달력 해시 불일치 / artifact 변조 / activated_at이 시계보다 늦음 → SESSION_CALENDAR_UNAVAILABLE:<reason>, 결과 파일 없음
   T4 --calendar로 다른 artifact → EXPLICIT_ARTIFACT_NOT_ACTIVE, 종가 미확인
   T5 이력 파일이 ACTIVE라고 적어도 달력 해시가 통합 권한과 다르면 실행기가 쓰지 않는다
   T6 이력 빌더: 통합 권한 일치 → ACTIVE / 불일치·로더 실패 → EXPLICIT_ARTIFACT_NOT_ACTIVE, 출력 JSON에 사유
   T7 두 스크립트의 argparse에 activation·manifest·trusted root를 받는 인자가 없다
3. 구현 → 대상 테스트:
   python -m unittest discover -s manage-us-stock-strategy/tests -p "test_s7_calendar_binding.py"
   같은 방식으로 test_run_portfolio_exposure_review.py, test_regular_session_close_history.py,
   test_portfolio_exposure_judge_fixes.py, test_integrated_authority_snapshot.py, test_session_authority.py
4. 전체 테스트를 서브에이전트로 1회 → 0단계 목록과 비교해 "새 실패"만 보고한다(목표 0).
   기존 테스트 단언을 바꿨으면 바꾼 것마다 전후 문장과 이유를 표로 적는다.
5. 보고 파일: 바꾼 파일과 diff --stat, 파일별 원시 sha256 전후, 고정 22개·정책 파일 해시 무변경 확인,
   테스트 결과, 남은 문제(이 지시문 4절 포함)를 적는다. 커밋하지 않는다(Judge와 사용자 승인 뒤).
```

## 4. 이번 범위 밖 (기록만)

| # | 내용 | 처리 |
|---|---|---|
| X1 | 옛 파일 `session_calendar_activation.json`은 그대로 남는다. 옛 경로(`session_authority.derive_us_market_session_authority`, 수동 분석의 LEGACY_INDEPENDENT fallback)는 계속 8/29 달력을 본다 | 이번에 바꾸지 않는다. 옛 파일을 정리하거나 은퇴시키려면 별도 K3 |
| X2 | 달력 `2421eeb7…`은 2026-12-31까지다. 2027년 첫 세션부터는 기본 실행이 `SESSION_CALENDAR_DOES_NOT_COVER_TODAY`로 멈춘다(fail-closed) | 12월 중에 2027년 달력 K3(통합 권한 갱신) |
| X3 | MU·DELL·AMD·TQQQ가 통합 권한의 신원 범위 밖에 있다(S7 보고 X14) | 별도 K3, 매수 전에 필요 |

## 5. 병합 뒤 Cowork 할 일

1. 원본 폴더(LF)에서 `run_portfolio_exposure_review.py`를 기본 입력으로 실행한다. 결과 폴더는 임시 경로로 둔다. 평가 세션이 최근 완료 세션으로 나오고 `SESSION_CALENDAR_DOES_NOT_COVER_TODAY`가 나오지 않는지 확인한다. 종가 이력이 없어서 생기는 R0는 예상된 결과다.
2. S7 보고 F1·U1과 S5 제안서 진행 기록의 "선행: 세션 달력 9월 이후 활성화(별도 K3)"를 "통합 권한 연결로 해소(이 문서)"로 고친다.
3. S7 병합 뒤 작업 3단계(30분봉 수집 → `regular_session_close_history.py build`)로 넘어간다.

## 6. 진행 기록

- 2026-10-02 Cowork 진단, 사용자가 선택 A를 고름, 이 지시문 작성.
- 2026-10-02 Builder 1단계 조사 완료(worktree `s7-cal-bind`, HEAD `9af9dfc`, 기준선 2228건 중 실패 22·오류 292). Cowork 검토: 제안 1~5 수용. 추가 조건 2개 — (가) `--calendar`를 줬는데 결과가 ACTIVE가 아니면 `non_default_inputs`에 `calendar`를 넣어 `[비표준 입력]` 표시, (나) 허용 파일에 `references/portfolio-exposure-review.md`를 더해 `:74` 달력 권한 문장과 비표준 입력 목록만 고친다(K0).
- 2026-10-02 Builder 완료(새 실패 0). Cowork 확인: 변경 8개(허용 범위), 대상 테스트 4개 VM 통과, 실제 Production 권한으로 ACTIVE·평가 세션 10-01 확인. Judge 지시문 `s7-calendar-binding-judge-prompt-2026-10-02.md` 작성.
- 2026-10-02 Judge 판정 PASS(J1~J9 PASS, 필수 수정 없음, 사용자 결정 없음, 전체 2238건 새 미통과 0). 선택 항목 b~d(테스트 보강, 예상 밖 예외 코드 통일, 테스트 정리)는 하지 않고 기록만 남김. e(실패·오류 구분 22·292 vs 23·291, ID 집합 동일)는 Builder 보고에 주석. 다음: Builder 커밋 → 사용자 병합 → Cowork 원본 폴더 확인.
- 2026-10-02 사용자 병합 `cd39212`. Cowork 원본 폴더 기본 실행 확인: 달력 2421eeb7 ACTIVE, calendar_authority LOADED(manifest c5ee680d), 평가 세션 2026-10-01(LATEST_COMPLETED_SESSION), non_default_inputs 비어 있음, 적용 시작 후보 NOT_READY(종가 이력 없음·CLOSE_MISSING — 예상대로), 상태·정책 파일 해시 실행 전후 같음. S7 보고 F1·U1·5.4-2와 S5 제안서 선행 문구에 해소 표시. 다음: S7 병합 뒤 작업 3단계(30분봉 수집 → close history build).
