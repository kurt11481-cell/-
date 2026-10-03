# p-earn Builder 지시문 — 실적 금지 구간 개정 구현 (2026-10-03, K3)

- 목적: 승인된 수정안 r1(`docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md`)의 3·4·5절을 구현한다. 확인된 미공지(`NOT_ANNOUNCED`)는 금지 구간이 아니고, 확인하지 못한 경우는 모두 금지로 남긴다.
- 사용자 승인(2026-10-03, Cowork 대화 원문): "p-earn r1 승인: 확인된 미공지는 금지 구간 아님, 확인 못 함은 금지 유지, D2는 S7 2단계로 이관, J4 남은 위험(표시 전용) 수용".
- 성격: K3. Builder가 끝나면 별도 세션의 Judge 2가 구현을 심사한다. `order_authority=false`, `quantity_authority=none`, `execution_quantity=null` 유지.
- 상태: 작성 완료, Builder 미실행.

## 1. 사용자 조작 (Windows 터미널)

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree `p-earn-impl` · 이유: K3 정책 파일과 판정 코드를 함께 바꾸고, 시간대(EDT·EST) 경계와 fail-closed 경로를 테스트로 고정해야 함**

1. 새 Windows 터미널에서 입력: `cd "E:\사업\##금동한\코덱스저장소"`
2. 문서 5개를 커밋한다(worktree는 커밋된 HEAD에서 만들어진다).
   `git add docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md docs/claude/p-earn-builder-prompt-2026-10-03.md docs/claude/integrated-stock-cards-v1-2026-10-02.md docs/claude/integrated-check-prompt-v3.8-draft-2026-10-03.txt manage-us-stock-strategy/references/portfolio-exposure-review.md`
   `git commit -m "docs: p-earn r1 approval and builder prompt, evidence docs, K0 token order note"`
3. `claude --worktree p-earn-impl`
4. 세션 안에서 `/model`로 Opus, `/effort`로 xhigh를 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `docs/claude/p-earn-builder-prompt-2026-10-03.md 3절 상자 안의 지시를 그대로 따르는 Builder로 일해라. 그 밖의 절은 참고만 한다.`
6. 권한 확인 창이 뜨면 다음 기준으로 고른다.
   - 허용: 파일 읽기, `git status`/`log`/`diff`/`show`/`rev-parse`, python 테스트·해시 계산, worktree 안 파일 쓰기.
   - 거부: 키움 도구 전부, 네트워크, `.env` 읽기, worktree 밖 파일 쓰기, `reconcile_broker_state.py apply`, `portfolio_review_journal.py apply`, `migrate_integrated_shadow_cohort.py`, 커밋·push·merge.
7. 끝나면 Cowork에 "Builder 완료, worktree p-earn-impl, 새 실패 수 N"만 보낸다. Builder가 질문하며 멈췄으면 그 질문을 붙여 넣는다.

- 2번의 `references/portfolio-exposure-review.md`는 10/3에 추가된 K0 절차 "Token order" 9줄(미커밋)이다. 먼저 커밋해야 Builder가 같은 파일을 고쳐도 병합 때 충돌하지 않는다.

## 2. Cowork 사전 확인 (2026-10-03, 읽기 전용)

| # | 사실 | 근거 |
|---|---|---|
| C1 | 줄바꿈: `alert_policy.json`·`portfolio_exposure.py`·`run_portfolio_exposure_review.py`·`test_portfolio_exposure.py`·`references/portfolio-exposure-review.md`는 CRLF(bare LF 0). S5 확정안 문서는 LF(CR 0) | 바이트 계수 |
| C2 | 기존 단언은 r1에서도 참이다: `None`·`UNVERIFIED` → `EARNINGS_DATE_UNVERIFIED`, 달력 밖 → `EARNINGS_WINDOW_NOT_CHECKABLE`, `blockers("DRAM", None)` 금지, `EARNINGS_DATE_STALE`, VERIFIED 구간 표 | `test_portfolio_exposure.py:413-450` |
| C3 | 실적 결과 코드 문자열은 `portfolio_exposure.py` 안에서만 쓰인다(표시·locale 매핑 없음) | `git grep` |
| C4 | `earnings_date_unverified` 키는 `alert_policy.json:813` 한 곳뿐이다(docs 제외) | `git grep` |
| C5 | `ZoneInfo`는 `run_portfolio_exposure_review.py`가 이미 쓴다(10/2 Windows 실행됨). Python 3.10의 `datetime.fromisoformat`은 "Z" 접미사를 받지 못한다 → 직접 처리 필요(사용자 PC Python 버전은 확인 필요) | `git grep`, VM Python 3.10.12 |
| C6 | `holding_timing_rules`는 `shadow_acceptance.semantic_fingerprint`의 대상이고(`:223-229`), `portfolio_exposure_policy`는 아니다 | 코드 |
| C7 | 노출 관련 테스트 파일: `test_portfolio_exposure.py`, `test_portfolio_exposure_display.py`, `test_portfolio_exposure_fail_closed.py`, `test_portfolio_exposure_judge_fixes.py`, `test_run_portfolio_exposure_review.py`, `test_s7_calendar_binding.py`, `test_corporate_actions.py`. 픽스처 `s5_exposure_fixtures.py` | `ls` |
| C8 | HEAD `9f0912e` 기준 blob: `alert_policy.json` `0a40505894935dbc05bd2b13fc4214f2cadc18d3`, `portfolio_exposure.py` `87d2920c471bca205aa113334c3728e6f7e631f4`, `run_portfolio_exposure_review.py` `4bef669139107c9ae298beea34dfd271729add92`, `test_portfolio_exposure.py` `0b5cbfba49febd913820801622fe35c9868c91c6`, `s5_exposure_fixtures.py` `60e62ed80cf7b7a3444fa58414e5069a9148e511`. 1절 2번 커밋은 이 파일들을 바꾸지 않는다 | `git rev-parse` |

## 3. Builder 지시 (이 상자만 따른다)

```text
역할: 투자_V2 Builder (K3, 사용자 승인 2026-10-03 "p-earn r1 승인"). 범위 = docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md(r1)의 2~5절 구현.
주문·수량 권한 없음. 키움 도구 호출 금지. 네트워크 금지. 비밀(.env*, 토큰, 계좌번호) 읽기 금지. 커밋·push·merge 금지.
먼저 수정안 r1 전체를 읽는다. 이 상자와 수정안이 다르면 멈추고 묻는다.

0단계 (고치기 전)
 a. 기준 확인: git rev-parse HEAD:<경로>가 아래와 같아야 한다. 다르면 멈추고 보고한다.
    stock-strategy-system/alert_policy.json 0a40505894935dbc05bd2b13fc4214f2cadc18d3
    manage-us-stock-strategy/scripts/portfolio_exposure.py 87d2920c471bca205aa113334c3728e6f7e631f4
    manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py 4bef669139107c9ae298beea34dfd271729add92
    manage-us-stock-strategy/tests/test_portfolio_exposure.py 0b5cbfba49febd913820801622fe35c9868c91c6
    manage-us-stock-strategy/tests/s5_exposure_fixtures.py 60e62ed80cf7b7a3444fa58414e5069a9148e511
    references/portfolio-exposure-review.md에 "Token order" 절이 있어야 한다.
 b. shadow_acceptance.semantic_fingerprint(<worktree 루트>) 값을 기록한다(읽기 전용 python).
 c. 대상 테스트(아래 2번 목록)를 파일마다 -p로 돌리고, 전체 테스트를 서브에이전트로 1회 돌려 기준 실패 목록을 만든다.
 d. 새 테스트를 먼저 쓰고, 고치기 전 코드에서 몇 개가 실패하는지 기록한다.

바꿔도 되는 파일(이것만):
- stock-strategy-system/alert_policy.json (수정안 3절 diff 그대로)
- manage-us-stock-strategy/scripts/portfolio_exposure.py
- manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py
- manage-us-stock-strategy/tests/test_portfolio_exposure.py, manage-us-stock-strategy/tests/test_run_portfolio_exposure_review.py
  (새 테스트 추가만. 기존 단언은 r1에서도 참이므로 바꾸지 않는다. 바꿔야 하면 멈추고 묻는다)
- manage-us-stock-strategy/references/portfolio-exposure-review.md
- docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md (10줄 "## S5 확정안 r2" 제목 바로 아래 개정 메모 1줄만)
- 새 docs/claude/p-earn-builder-report-2026-10-03.md (보고)
그 밖의 파일은 고치지 않는다. 특히: alert_policy.json의 holding_timing_rules·holding_risk_rules·최상위 policy_version·strategy_version·
권한 필드·deployment_gate·portfolio_review_lines(834줄 policy_version 포함), workspace/policies/*, workspace/state/*, portfolio_state.json,
shadow_acceptance.py, s5_exposure_fixtures.py(도우미가 필요하면 테스트 파일 안에 둔다), 스키마 파일, 키움 고정 16개, deployment_gate 고정 6개.
목록 밖을 바꿔야 하면 멈추고 묻는다.

요구:
R1 earnings_blackout(symbol, earnings, calendar_sessions, buy_session, *, evaluation_session=None, generated_at=None):
   - 기록이 dict가 아니면 (True, "EARNINGS_DATE_UNVERIFIED").
   - status == "VERIFIED": 지금 코드 그대로(구간 계산·코드·순서 무변경).
   - status == "NOT_ANNOUNCED"(정확히 이 문자열): 수정안 2절 2번의 단계를 그 순서대로.
     1) buy_session·evaluation_session이 None이거나 calendar_sessions에 없으면 EARNINGS_WINDOW_NOT_CHECKABLE
     2) 기록에 "announcement_session" 또는 "timing" 키가 있으면 EARNINGS_RECORD_CONTRADICTORY
     3) source_kind ∈ {COMPANY_IR, COMPANY_PRESS_RELEASE, SEC_FILING}, source_url은 str이고 "https://"로 시작하며
        urllib.parse.urlsplit(url).hostname이 비어 있지 않음, checked_at은 str이고 파싱되며 UTC 오프셋이 있음.
        하나라도 아니면 EARNINGS_CHECK_SOURCE_INVALID
     4) generated_at이 str이 아니거나 파싱 불가·오프셋 없음이면 EARNINGS_CHECK_GENERATED_AT_INVALID
     5) checked_at > generated_at이면 EARNINGS_CHECK_FUTURE_TIMESTAMP
     6) checked_at < evaluation_session 날짜 16:00 ZoneInfo("America/New_York")이면 EARNINGS_CHECK_STALE (16:00 정각은 통과)
     7) 모두 통과하면 (False, "EARNINGS_NOT_ANNOUNCED_CHECKED")
   - 그 밖의 status(소문자 포함)는 (True, "EARNINGS_DATE_UNVERIFIED").
   - ISO 파싱: 끝의 "Z"는 "+00:00"으로 바꿔 읽는다(Python 3.10 호환). 잡는 예외는 ValueError·TypeError뿐이고 해당 금지 코드로 보낸다.
     넓은 except, 기본값으로 통과시키기, .get(key, 통과값) 금지.
   - 모듈은 시계(datetime.now 등)를 읽지 않는다.
R2 increase_blockers와 build_exposure_review에 같은 키워드 인자(evaluation_session, generated_at, 기본 None)를 더해 earnings_blackout까지 넘긴다.
   MU→DRAM 대체 금지 판정과 제안 경로(:1293 부근 blockers)도 같은 인자로 부른다. build_exposure_review는 자기 evaluation_session을 넘긴다
   (매수 세션에서 거꾸로 추정하지 않는다). 기본 None이면 NOT_ANNOUNCED만 금지로 가고 VERIFIED·그 밖 경로는 지금과 같다.
R3 run_portfolio_exposure_review.py: 출력 "generated_at"(:418)과 같은 문자열 값을 build_exposure_review(generated_at=...)에 넘긴다.
   --earnings 도움말에 NOT_ANNOUNCED 형식을 더한다. 그 밖의 동작은 바꾸지 않는다.
R4 alert_policy.json: 수정안 3절 diff만. 704줄 값 1개 변경, 813줄 1줄을 3절의 새 3줄로 교체(같은 위치, 같은 들여쓰기).
   CRLF 유지, 다른 줄 바이트 무변경. JSON 키 경로로 펴서 비교했을 때 바뀐 경로가 정확히 5개
   (portfolio_exposure_policy.policy_version 값, earnings_date_unverified 삭제, 새 키 3개 추가)인지 확인한다.
R5 references/portfolio-exposure-review.md: 26줄 R3 문구를 r1 규칙으로 바꾸고, --earnings 입력 형식·NOT_ANNOUNCED 조건·결과 코드·
   구간 읽기 규칙(earnings_blackout_window_reading)을 짧은 절로 더한다. "Token order" 절은 그대로. CRLF.
R6 S5 확정안 문서: 10줄 제목 바로 아래에 수정안 4절의 개정 메모 1줄(날짜는 오늘). 본문은 바꾸지 않는다. LF.
R7 docstring·주석을 새 규칙에 맞춘다. 새 의존성 없음. 그 밖의 동작 변경 없음.

테스트(수정안 5절 1~12번 전부를 새 테스트로):
 경계 시각은 EDT 평가 세션(기존 EVAL 2026-09-30: 19:59Z 금지·20:00Z 통과)과 EST 평가 세션(2026-11-02 이후 달력의 정규장 세션:
 20:59Z 금지·21:00Z 통과)을 모두 넣는다. 지문 불변 테스트(12번)는 0단계 b의 값과 변경 뒤 값을 보고에 적는 것으로 대신해도 된다.

1. 구현한 뒤 대상 테스트를 파일마다 -p로 돌린다: test_portfolio_exposure.py, test_portfolio_exposure_display.py,
   test_portfolio_exposure_fail_closed.py, test_portfolio_exposure_judge_fixes.py, test_run_portfolio_exposure_review.py,
   test_s7_calendar_binding.py, test_corporate_actions.py, test_v2_6_7_session_aware_kiwoom_priority.py.
   스키마 감사: python manage-us-stock-strategy/scripts/validate_schema_contracts.py
2. 전체 테스트를 서브에이전트로 1회 돌리고, 0단계 목록과 비교해 "새 실패"만 보고한다(목표 0).
3. semantic_fingerprint가 0단계 b 값과 같은지 확인한다.
4. 보고 파일에 적는다: 바꾼 파일과 git diff --stat, 파일별 원시 sha256 전후, 줄바꿈 확인(CRLF/LF, bare LF 0, BOM 없음),
   alert_policy.json 키 경로 diff, 지문 전후, 테스트 결과(고치기 전 새 테스트 실패 수, 기준 실패 vs 새 실패), 남은 문제.
5. 보고 직전 자기 점검 한 줄: "fail-open 6종(Partial·Stale·Missing·Unknown·Deny-list·Swallowed)을 새 결정 경로마다 대어 봤다: 예/아니오(이유)".
커밋하지 않는다.
```

## 4. 이번 범위 밖 (기록만)

- 수정안 7절 F1~F7: `event_risk_policy.json` 옛 경로, 2027 달력, `--earnings` 자동 생성기, VERIFIED 출처 요구, D2(539줄)는 S7 2단계, v3.8 ① 칸 문구(K1), MU·NBIS 공지 리드타임 기록.

## 5. Builder 뒤 순서

1. Cowork: worktree 읽기 전용 확인(git status·diff --stat, 허용 목록, 금지 파일 무변경, 줄바꿈, alert_policy 키 경로 diff, 대상 테스트 재실행).
2. Cowork: Judge 2 지시문 작성 → 사용자가 별도 세션에서 실행.
3. Judge 2 PASS → 사용자 커밋·병합(Windows 터미널) → Cowork 읽기 전용 확인, 관제판 p-earn 완료.
4. 병합 뒤 첫 노출 점검부터 Cowork가 `--earnings` 파일(공식 출처 확인 기록)을 만들어 넣는다.

## 6. 진행 기록

- 2026-10-03 Cowork: 사용자 승인 뒤 작성. Builder 미실행.
