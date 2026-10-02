# S7 달력 연결 Independent Judge 지시문 (2026-10-02)

- 대상: worktree `s7-cal-bind`(HEAD `9af9dfc`)의 **커밋 전 변경** 8개. 고친 파일 6개(스크립트 2, 참고 문서 1, 테스트 3)와 새 파일 2개(`tests/test_s7_calendar_binding.py`, Builder 보고 `docs/claude/s7-calendar-binding-builder-report-2026-10-02.md`)다.
- 근거: 원본 폴더 `E:\사업\##금동한\코덱스저장소\docs\claude\s7-calendar-binding-builder-prompt-2026-10-02.md`의 2절(사실 C1~C9), 3절(요구 R1~R7, T1~T7), 6절(1단계 뒤 사용자 추가 조건 (가)·(나)).
- 성격: K2 런타임 계약이지만 권한 연결을 바꾸는 변경이라 독립 심사를 받는다. Judge는 파일을 고치지 않는다. 주문·수량 권한은 없다.
- Cowork 사전 확인(10-02, 읽기 전용):
  - git status는 위 8개뿐이다.
  - 대상 테스트 4개 파일(새 파일 10, 이력 14, 실행기 17, JF 29)이 VM의 Linux Python 3.10에서 모두 통과했다.
  - **원본 폴더(LF)의 실제 Production 통합 권한**으로 worktree 코드를 읽기 전용으로 실행했다. 로더 OK, 달력 `2421eeb7…`(2026-09-03.1, ~12-31) ACTIVE, `calendar_authority` LOADED(manifest `c5ee680d…`, cohort `identity-confirmation-approved-20260922T234229Z`), 기본 평가 세션 `2026-10-01`(`LATEST_COMPLETED_SESSION`). 8/29 달력을 `--calendar`로 주면 `EXPLICIT_ARTIFACT_NOT_ACTIVE` / `CALENDAR_HASH_NOT_ACTIVE_AUTHORITY`가 나온다.
- 상태: 작성 완료, Judge 미실행.

## 1. 사용자 조작 (Windows 터미널)

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(Builder worktree 폴더에서, 새 worktree 아님) · 이유: 권한 연결 변경 독립 심사, 커밋 전 변경을 그대로 봐야 함, 파일 수정 없음**

1. Builder 창은 닫지 말고 그대로 둔다(수정이 필요하면 다시 쓴다). 새 Windows 터미널을 연다.
2. `cd "E:\사업\##금동한\코덱스저장소\.claude\worktrees\s7-cal-bind"`를 입력한다.
3. `claude`를 입력한다(`--worktree` 없이).
4. 세션 안에서 `/model`로 Opus를, `/effort`로 xhigh를 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `원본 폴더 파일 E:\사업\##금동한\코덱스저장소\docs\claude\s7-calendar-binding-judge-prompt-2026-10-02.md 3절 상자 안의 지시를 그대로 따르는 Judge로 일해라. 파일을 고치지 마라.`
6. 권한 확인 창: 읽기, git 읽기 명령, python 테스트·해시 계산, worktree 밖 파일 읽기는 허용한다. 파일 쓰기·수정·삭제, 커밋, 키움 도구는 거부한다.
7. 끝나면 마지막 "달력 연결 판정" 블록만 복사해 Cowork에 붙여 넣는다.

## 2. 판정 뒤 처리

- PASS: Builder 창에서 커밋 → 사용자 병합 → Cowork가 원본 폴더에서 확인(Builder 지시문 5절).
- PASS_WITH_FIXES: Cowork가 Builder 수정 지시를 쓴다 → 같은 Builder 창에서 최소 수정 → 같은 Judge 창에서 "수정 재확인, 필수 수정 항목만".
- FAIL: 사용자 결정 항목을 Cowork에서 하나씩 정한다.

## 3. 붙여넣기용 지시문

```text
역할: S7 달력 연결 Independent Judge. 대상은 현재 폴더(worktree s7-cal-bind)의 커밋 전 변경이다.
금지: 파일 수정·생성·삭제·이동, 커밋·브랜치 변경, 키움 도구, 주문 도구, .env*·토큰·계좌번호 읽기, 네트워크 조회,
      reconcile_broker_state.py apply, portfolio_review_journal.py apply.
허용: 파일 읽기(worktree 밖은 E:\사업\##금동한\코덱스저장소\ 아래 읽기만), git 읽기 명령(status/diff/show/log/rev-parse/ls-files),
      python 해시·산술, 테스트 실행(PYTHONDONTWRITEBYTECODE=1, worktree에 결과 파일을 남기지 않음). 전체 테스트는 서브에이전트로.
Builder 보고는 단서일 뿐이다. diff·코드·테스트 출력으로 확인한다. 없는 수치는 만들지 않는다(확인 필요 / NOT VERIFIED).
보고는 한국어, 식별자는 영어.

0. 기준 확인(다르면 멈추고 보고)
   - HEAD 9af9dfc. git status가 고친 6개(scripts/run_portfolio_exposure_review.py, scripts/regular_session_close_history.py,
     references/portfolio-exposure-review.md, tests/test_run_portfolio_exposure_review.py, tests/test_regular_session_close_history.py,
     tests/test_portfolio_exposure_judge_fixes.py) + 새 2개(tests/test_s7_calendar_binding.py, docs/claude/s7-calendar-binding-builder-report-2026-10-02.md)뿐인지.
   - 읽기: CLAUDE.md, 원본 폴더 docs/claude/s7-calendar-binding-builder-prompt-2026-10-02.md 2·3·4·6절,
     worktree의 Builder 보고 전체, scripts/integrated_authority_snapshot.py(로더·_freeze), schemas/regular-session-close-history.schema.json.
1. 판정 항목
   J1 범위: 변경이 허용 파일 7개 안에 있는지. workspace/policies/*(두 activation 파일), integrated_authority_snapshot.py,
      session_authority.py, session_calendar_artifact.py, schemas/*, alert_policy.json이 HEAD와 같은지. 고친 파일의 줄바꿈·BOM 유지.
      참고 문서 diff가 74~77행 문장 교체뿐인지(K0).
   J2 권한 출처(R1·R2): 두 스크립트가 달력 권한을 load_production_integrated_authority_snapshot 하나에서만 얻는지.
      옛 session_calendar_activation.json·DEFAULT_ACTIVATION 참조가 남지 않았는지. 권한 파일·trusted root를 바꾸는
      명령 인자·환경변수가 없는지(TRUSTED_ROOT 모듈 상수만). ACTIVE = 로더 성공 AND 원시 sha256 == snapshot.session.calendar_hash.
   J3 fail-closed(R3): 로더 실패 5종(파일 없음, SHADOW, 해시 불일치, artifact 변조, activated_at > 시계)에서 기본 실행이
      SESSION_CALENDAR_UNAVAILABLE:<reason>으로 멈추고 결과 파일이 없는지. --calendar + 로더 실패/다른 해시 → EXPLICIT,
      종가 미확인, non_default_inputs에 "calendar", inputs.calendar_authority UNAVAILABLE, 적용 시작 후보 NOT_READY인지.
      load_production_snapshot이 IntegratedAuthorityLoadError 말고 다른 예외를 만나면 어떻게 되는지(열린 채 통과하는 경로가 없는지).
   J4 이력 파일 계약: 이력 파일 calendar 블록 키 5개와 상태 값 2개가 그대로인지(스키마). authority_failure가 이력 파일에
      들어가지 않는지. 실행기가 이력 파일의 authority_status를 믿지 않고 다시 판정하는지.
   J5 calendar_from_snapshot: _thaw가 _freeze의 역인지, 로더가 이미 검증한 artifact를 다시 schema·semantic 검증하는지,
      같은 LF 파일을 load_calendar로 읽은 결과와 sessions·identity가 같은지(픽스처로 직접 비교).
   J6 시점·출처(R4·R5): decision_as_of = 실행 시각 또는 --now. inputs.calendar_authority 키(LOADED 4개 / UNAVAILABLE+reason).
      inputs.calendar 키 구성 무변경. non_default_inputs 순서("calendar"가 "now" 앞)가 표시·적용 시작 판정에 영향을 주는지.
   J7 단언 보존: Builder 보고 4절 표의 바뀐 단언 5곳이 같은 뜻을 지키는지. 특히 test_calendar_that_is_not_active_leaves_every_close_unverified의
      non_default_inputs [] → ["calendar"] 변경이 사용자 조건 (가)로만 설명되는지.
   J8 테스트: 새 테스트 10개가 사례를 실제로 단언하는지(동어반복·항상 참 아님). T2(옛 파일 무시)와 T3(5종)는 본문을 직접 읽는다.
      대상 5개 파일(새 파일, 실행기, 이력, JF, test_session_authority)을 직접 실행한다. 전체 테스트는 서브에이전트 1회로 돌려
      미통과 ID를 docs/claude/s7-builder-stage4-test-failures-2026-10-01.txt와 비교한다. 목록에 없는 미통과가 있으면
      이번 변경과의 관련을 판정한다(worktree CRLF 때문인 기존 실패는 새 실패가 아님).
   J9 적대 점검: 옛 파일을 고치거나 다른 달력을 --calendar로 넣거나 이력 파일에 ACTIVE를 적거나 시계를 바꾸는 방법(--now)으로
      미확인 종가를 확인된 것처럼 만들거나 적용 시작 후보를 READY로 만들 수 있는지.

판정 기준: PASS = 그대로 커밋 가능. PASS_WITH_FIXES = 같은 Builder의 최소 수정으로 해소, 사용자 새 결정 없음.
FAIL = 사용자 결정 또는 설계 변경 필요.

출력: 마지막에 아래 블록 하나(35줄 이내). 앞에 긴 설명을 붙이지 않는다.
달력 연결 판정
- 기준: HEAD, git status 일치 여부
- 최종: PASS / PASS_WITH_FIXES / FAIL
- J1~J9: PASS/FIX/FAIL + 한 줄 근거(파일:행 또는 테스트 이름)
- 테스트: 실행 수·새 미통과 수(전체, 대상)
- 필수 수정(커밋 전, Builder): 번호 목록
- 병합 뒤 작업에 더할 것: 번호 목록
- 사용자 결정 필요: 질문 형태로(없으면 "없음")
```

## 4. 진행 기록

- 2026-10-02 작성(Cowork). Builder 완료(새 실패 0 보고) 뒤 Cowork 읽기 전용 확인(diff, 대상 테스트 재실행, 실제 권한으로 읽기 실행)을 거쳐 작성.
- 2026-10-02 Judge 판정 PASS(J1~J9 PASS, 필수 수정 없음, 사용자 결정 없음, 전체 2238건 새 미통과 0). 선택 항목 b~d(테스트 보강, 예상 밖 예외 코드 통일, 테스트 정리)는 하지 않고 기록만 남김. e(실패·오류 구분 22·292 vs 23·291, ID 집합 동일)는 Builder 보고에 주석. 다음: Builder 커밋 → 사용자 병합 → Cowork 원본 폴더 확인.
- 2026-10-02 사용자 병합 `cd39212`. Cowork 원본 폴더 기본 실행 확인: 달력 2421eeb7 ACTIVE, calendar_authority LOADED(manifest c5ee680d), 평가 세션 2026-10-01(LATEST_COMPLETED_SESSION), non_default_inputs 비어 있음, 적용 시작 후보 NOT_READY(종가 이력 없음·CLOSE_MISSING — 예상대로), 상태·정책 파일 해시 실행 전후 같음. S7 보고 F1·U1·5.4-2와 S5 제안서 선행 문구에 해소 표시. 다음: S7 병합 뒤 작업 3단계(30분봉 수집 → close history build).
