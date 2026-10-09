# e-filing-feed K2 Builder 지시문 — SEC 섀도 수집기 감시 명단 교체 (2026-10-05)

[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: high · 세션: 새 worktree (`claude --worktree sec-watchlist`) · 이유: 스크립트 2개·PowerShell 1개·규칙 JSON·테스트 2개에 걸친 K2 변경(런타임 계약), 대상 테스트로 검증

근거: `docs/claude/e-filing-feed-review-2026-10-05.md` (사용자 채택 2026-10-05). 등급 K2. Kiwoom acceptance pin 범위 밖(확인: pin-scope에 sec 파일 없음 — Builder가 다시 확인).

## 목표
읽기 전용 SEC 섀도 수집기(`sec_official_event_intake.py`, `sec_scheduled_shadow.py`)의 감시 명단을 현재 대상으로 바꾼다. 수집 방식·접속 호스트·요청 속도·권한 필드는 바꾸지 않는다.

- 새 명단: holdings = MRVL, NBIS (MVLL→MRVL 파생 관계 유지, SOXL은 기존대로 DEFERRED) / watch = MU, BE, DELL, PWR, LITE
- 제외: PGR, JPM, CME, V (옛 challengers)

## 할 일
1. `manage-us-stock-strategy/assets/sec-official-event-intake-rules-v0.1.json`: `corporate_watchlist`, `holdings` 갱신, `challengers`를 `watch`로 교체(키 이름 변경이 스키마·코드에 걸리면 가장 작은 변경을 고르고 보고). `root_theses`는 새 종목에 값을 지어내지 않는다 — 필수 필드면 `["UNCLASSIFIED"]`.
2. 하드코딩 제거: `sec_official_event_intake.py` 827행 근처(PGR 요약 줄)·896행 근처(6종목 튜플), `run_sec_scheduled_shadow.ps1` 80행(`"MRVL,NBIS,PGR,JPM,CME,V"` 비교) — 규칙 파일의 명단에서 읽도록 바꾼다. 다른 스크립트(save_daily_pipeline, tactical radar 등)의 PGR 언급은 범위 밖, 건드리지 않는다.
3. `route_materiality`: watch 종목은 portfolio_relevance를 "WATCHLIST"로, 8-K 중요 항목(`material_8k_items`)·`high_candidate_event_types`는 materiality HIGH, decision_impact는 "WATCH"(보유가 아니므로 ASSET_REVIEW_REQUIRED 아님). 보유 종목 경로는 그대로.
4. 테스트 갱신: `tests/test_sec_official_event_intake.py`, `tests/test_sec_scheduled_shadow.py`의 명단 기대값. 합성 fixture(`tests/fixtures/sec/company_tickers_exchange.synthetic.json`)에 새 종목이 필요하면 합성 값으로 추가(실제 CIK를 지어내지 않는다 — 합성임을 표시).
5. 실행: 대상 테스트 2개 → `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`. 전체 스위트는 서브에이전트에서 돌리고 실패만 보고.

## 금지
- sec.gov 실제 접속(테스트는 fixture만), 작업 스케줄러 등록·사용 설정 변경, `SEC_USER_AGENT` 읽기·출력.
- 정책·상태 파일, decision_journal.json 수정. 주문 경로. 커밋·푸시(사용자가 함).
- 줄바꿈 일괄 변환(CRLF 유지).

## 알려진 기존 실패 (회귀로 세지 않음, 상태 변화만 보고)
`test_sec_scheduled_shadow` 01·05·23(PowerShell `Join-Path` 빈 `$PSScriptRoot`), 35·37(`SEC_ACCESS_BLOCKED` 종료 코드 1≠7) — `docs/claude/i4-r9-activation-report-2026-10-05.md`.

## 보고 (docs/claude/e-filing-feed-k2-builder-report-2026-10-05.md, 한국어)
바뀐 파일·줄 수, 테스트 결과(전·후 실패 id), 스키마 감사 결과, 남은 하드코딩 위치, 확인 필요.
보고 전 자기 점검 한 줄(fail-open 점검표): 명단 파일을 못 읽거나 비었을 때 조용히 0건 PASS가 되지 않고 실패로 끝나는가? 대체 경로가 권한을 물려받지 않는가?
