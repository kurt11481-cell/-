# p-earn Judge 2 지시문 — 실적 금지 구간 개정 구현 심사 (2026-10-03, K3)

- 대상: worktree `p-earn-impl`(브랜치 `worktree-p-earn-impl`, HEAD `906f7651c37d525d5ebae4c2f2c85b36a9283336`)의 **커밋 전 변경**: 고친 파일 7개 + 새 보고 `docs/claude/p-earn-builder-report-2026-10-03.md`.
- 근거 문서(HEAD `906f765`에 있음): 수정안 r1 `docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md`(2~6절, 8절 Judge 1 결과, 9절 사용자 승인 원문), Builder 지시문 `docs/claude/p-earn-builder-prompt-2026-10-03.md` 3절.
- 성격: K3 구현 심사. Judge는 파일을 고치지 않는다. 주문·수량 권한 없음.
- 상태: 작성 완료, Judge 2 미실행.

## 1. 사용자 조작 (Windows 터미널)

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(Builder worktree 폴더에서, 새 worktree 아님) · 이유: K3 구현 독립 심사, 커밋 전 변경을 그대로 봐야 함, 파일 수정 없음**

1. Builder 창은 닫지 말고 그대로 둔다(수정이 필요하면 다시 쓴다). 새 Windows 터미널을 연다.
2. `cd "E:\사업\##금동한\코덱스저장소\.claude\worktrees\p-earn-impl"`를 입력한다.
3. `claude`를 입력한다(`--worktree` 없이).
4. 세션 안에서 `/model`로 Opus, `/effort`로 xhigh를 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `원본 폴더 파일 E:\사업\##금동한\코덱스저장소\docs\claude\p-earn-judge2-prompt-2026-10-03.md 3절 상자 안의 지시를 그대로 따르는 p-earn Judge 2로 일해라. 파일을 고치지 마라.`
6. 권한 확인 창: 읽기, git 읽기 명령, python 테스트·해시 계산, worktree 밖 파일 읽기는 허용. 파일 쓰기·수정·삭제, 커밋, 키움 도구는 거부.
7. 끝나면 마지막 "p-earn Judge 2 판정" 블록만 복사해 Cowork에 붙여 넣는다.

## 2. Cowork 사전 확인 (2026-10-03, 읽기 전용) · 판정 뒤 처리

| # | 확인 | 결과 |
|---|---|---|
| C1 | `git status` | 고친 파일 7개(`alert_policy.json`, `portfolio_exposure.py`, `run_portfolio_exposure_review.py`, `test_portfolio_exposure.py`, `test_run_portfolio_exposure_review.py`, `references/portfolio-exposure-review.md`, S5 확정안 문서) + 새 보고 1개. 모두 Builder 허용 목록 안 |
| C2 | `alert_policy.json` 키 경로 diff | 정확히 5개: `portfolio_exposure_policy.policy_version` 값, `earnings_date_unverified` 삭제, `earnings_blackout_window_reading`·`earnings_date_not_announced`·`earnings_check_missing_stale_or_unknown` 추가. 줄 diff(CRLF 정규화)는 704줄 1개, 813줄 → 813~815줄뿐 |
| C3 | 줄바꿈 | 바뀐 파일 모두 CRLF·bare LF 0·BOM 없음(worktree 체크아웃 형식. S5 문서는 blob이 LF이고 autocrlf로 CRLF 체크아웃 — Builder 보고 8절 1번) |
| C4 | 테스트 파일 diff | 삭제 0줄(추가만: 291줄, 46줄) |
| C5 | 대상 테스트(VM Linux Python 3.10.12) | `test_portfolio_exposure.py` 57, `_display` 7, `_fail_closed` 32, `_judge_fixes` 29, `test_run_portfolio_exposure_review.py` 24, `test_s7_calendar_binding.py` 10, `test_corporate_actions.py` 27 — 모두 OK. `test_v2_6_7_session_aware_kiwoom_priority.py` 15 FAIL은 변경 없는 worktree `judge-p-earn`(`9f0912e`)에서도 같은 15건(환경 요인), cohort 테스트(`:505-515`)는 통과. Builder 보고(Windows) 기준 14건 = 변경 뒤 14건 |
| C6 | `shadow_acceptance.semantic_fingerprint` | worktree = 원본 폴더 = `628c60818f3beeb255e28e28abd99677f4848f3833fe5a0c83c14e7d304011a0` |
| C7 | `portfolio_exposure.py` 시계 사용 | `datetime.now`·`time.time`·`date.today` 0건 |
| C8 | Builder 보고 9절 남은 문제 1(모르는 키 무시)·2(세션 인접성 미확인) | 3절 K3·K4로 질문. 사용자 PC Python 3.13.15 + tzdata 2026.3은 Builder 보고 값(Cowork 미검증) |

기준 해시(worktree 원시 sha256 앞 16자): `alert_policy.json` `ebc8b8b28bf26206`(LF 정규화 `ba0ab8b99146565d`), `portfolio_exposure.py` `81130d05c8ab7a96`, `run_portfolio_exposure_review.py` `aa137f200371ccf4`, `test_portfolio_exposure.py` `6c739196dded1ed8`, `test_run_portfolio_exposure_review.py` `77d0acf0c09a50e6`, `references/portfolio-exposure-review.md` `ad931fd49fb46573`, S5 확정안 `6ace18abab7bdf57`, Builder 보고 `f097879b74adb705`.

판정 뒤 처리:

- PASS: Cowork가 커밋·병합 명령을 안내하고, 사용자가 Windows 터미널에서 실행한다. 병합 뒤 Cowork가 읽기 전용으로 확인한다.
- PASS_WITH_FIXES: Cowork가 Builder 수정 지시를 쓴다 → 같은 Builder 창에서 최소 수정 → 같은 Judge 창에 "수정 재확인, 필수 수정 항목만".
- FAIL: 사용자 결정이 필요한 항목을 Cowork에서 하나씩 정한다 → Builder 수정 → 재심사.

## 3. 붙여넣기용 지시문

```text
역할: p-earn Judge 2 (K3 구현 심사). 대상은 현재 폴더(worktree p-earn-impl)의 커밋 전 변경이다.
금지: 파일 수정·생성·삭제·이동, 커밋·브랜치 변경, 키움 도구, 주문 도구, .env*·토큰·계좌번호 읽기, 네트워크 조회,
      reconcile_broker_state.py apply, portfolio_review_journal.py apply, migrate_integrated_shadow_cohort.py.
허용: 파일 읽기(worktree 밖은 E:\사업\##금동한\코덱스저장소\ 아래 읽기만), git 읽기 명령(status/diff/show/log/rev-parse/ls-files/check-ignore),
      python 해시·산술, 테스트 실행(PYTHONDONTWRITEBYTECODE=1, 결과 파일을 worktree에 남기지 않음), 메모리 안 monkeypatch 실험(파일 쓰기 없음).
      긴 전체 테스트는 서브에이전트로.
Builder 보고는 단서일 뿐이다. diff·코드·테스트 출력으로 확인한다. 없는 수치는 만들지 않는다(확인 필요 / NOT VERIFIED).
보고는 한국어, 식별자는 영어.

0. 기준 확인(다르면 멈추고 보고)
   - git rev-parse HEAD = 906f7651c37d525d5ebae4c2f2c85b36a9283336
   - git status: 고친 파일 7개 + 새 docs/claude/p-earn-builder-report-2026-10-03.md 뿐(원본 폴더 docs/claude/p-earn-judge2-prompt-2026-10-03.md 2절 C1 목록).
   - 고친 파일의 원시 sha256 앞 16자가 지시문 2절 "기준 해시"와 같다.

1. 읽을 것
   - 수정안 r1 2~6절과 9절(승인 원문), Builder 지시문 3절, Builder 보고 전체(단서).
   - git diff HEAD 전체(7개 파일).
   - CLAUDE.md, manage-us-stock-strategy/references/development-change-review.md "Fail-open patterns"(6종).

2. 직접 확인
   a. alert_policy.json: 키 경로 diff가 정확히 5개인지, 줄 diff가 704·813(→813~815)뿐인지, holding_timing_rules·holding_risk_rules·
      최상위 policy_version·strategy_version·권한 필드·deployment_gate·portfolio_review_lines(834줄)가 그대로인지. CRLF 유지.
   b. earnings_blackout: NOT_ANNOUNCED 단계 순서와 결과 코드가 r1 2절 2번과 같은지, VERIFIED 경로가 바이트 수준으로 동작 무변경인지,
      그 밖의 status·dict 아님이 EARNINGS_DATE_UNVERIFIED인지. 잡는 예외가 ValueError·TypeError뿐인지.
   c. evaluation_session·generated_at이 add 경로, 제안 경로(blockers 클로저), MU→DRAM 판정에 모두 전달되는지.
      build_exposure_review가 자기 evaluation_session을 넘기는지. 러너가 출력 generated_at과 같은 문자열을 넘기는지. 모듈이 시계를 읽지 않는지.
   d. 테스트: r1 5절 1~12번 각각을 고정하는 테스트 이름 대응표를 만든다. 기존 단언 무변경(삭제 0). 고정 오프셋(−04:00) 구현으로 바꾸면
      EST 경계 테스트가 실패하는지 메모리 안 monkeypatch로 확인한다(가능하면).
   e. 대상 테스트를 파일마다 -p로 실행: test_portfolio_exposure.py, test_portfolio_exposure_display.py, test_portfolio_exposure_fail_closed.py,
      test_portfolio_exposure_judge_fixes.py, test_run_portfolio_exposure_review.py, test_s7_calendar_binding.py, test_corporate_actions.py,
      test_v2_6_7_session_aware_kiwoom_priority.py. v2_6_7 실패가 있으면 변경 전(HEAD) 같은 환경 결과와 ID를 비교한다.
      전체 테스트는 서브에이전트로 1회, Builder 보고의 기준 실패 목록과 ID 비교(새 실패 0인지).
   f. shadow_acceptance.semantic_fingerprint(worktree 루트) = 628c60818f3beeb255e28e28abd99677f4848f3833fe5a0c83c14e7d304011a0.
   g. 문서: references 새 절이 r1 규칙·코드와 같은지, "Token order" 절 보존, S5 확정안 메모 1줄(줄 번호 표기 포함)이 맞는지.
   h. 범위: workspace/policies/*, workspace/state/*, portfolio_state.json, shadow_acceptance.py, s5_exposure_fixtures.py, 스키마,
      키움 고정 16개, deployment_gate 고정 6개가 변경 목록에 없는지.

3. 판정 질문 — 각각 PASS / FAIL / 조건부 + 근거(파일:줄)
   K1 r1 2절 규칙(VERIFIED / NOT_ANNOUNCED 7단계 / 그 밖)이 코드와 일치하는가.
   K2 fail-open 6종(Partial·Stale·Missing·Unknown·Deny-list·Swallowed)이 새 결정 경로마다 막혀 있는가.
   K3 Builder 보고 9절 1번: NOT_ANNOUNCED 기록의 모르는 키(예: 오타 "announcement_date")가 무시되고 통과할 수 있다.
      지금대로 둘지, 허용 키 목록(status·source_kind·source_url·checked_at 등)으로 막아야 하는지 판단과 근거.
   K4 Builder 보고 9절 2번: buy_session과 evaluation_session의 인접성을 함수가 확인하지 않는다. 실제 경로(build_exposure_review)에서 위험이 있는가.
   K5 러너 --now로 generated_at이 바뀔 수 있다. 비표준 입력 표시(non_default "now")로 충분한가.
   K6 범위·지문·문서·줄바꿈.

4. 출력 (마지막에 이 블록 하나)
p-earn Judge 2 판정
- 결론: PASS | PASS_WITH_FIXES | FAIL
- 기준 확인: 일치 / 불일치(내용)
- K1~K6: 판정 · 근거 한 줄씩
- 5절 사례 대응표: 1~12 → 테스트 이름(없으면 "없음")
- 필수 수정(번호): 없으면 "없음"
- 권고(선택):
- 확인 못 한 것:
- 자기 점검: fail-open 6종을 각 결정 경로에 대어 봤다 — 예/아니오(이유)
```

## 4. 진행 기록

- 2026-10-03 Cowork: Builder 완료 보고("새 실패 수 0") 뒤 worktree 읽기 전용 확인(2절), 이 지시문 작성. Judge 2 미실행.
