---
id: event-ctx2-builder-prompt
title: 이벤트 노출 — 채점기 사후 계산 + 개장 전 점검용 표시 도구 (코어 변경 없음)
date: 2026-10-14
class: general (권한 경로 없음 — auto_core*.py·권한 스키마·카드 근거 등록부·정책·일지·결정 파일 무변경. tools/dev_pipeline/authority-paths.txt 대조 2026-10-13 23:5x KST)
supersedes: event-ctx(코어 decide가 일정표를 읽는 원안). 폐기 이유: CLAUDE.md:40 "코어의 LLM 입력은 06:40 통합 점검 연구 기록뿐"과 충돌(일정표는 예약 LLM 작업이 사람 확인 없이 덧붙이는 파일), 권한 경로라 t1-safety 병합 대기, 체결 시각 16:00 고정(조기 폐장 무시), 매도에도 "떠안음" 문구. 초안은 docs/claude/_to_delete/event-ctx-builder-prompt.md
source: 사용자 지시 "전략 문서의 수립한 전략을 자동화 운영 시스템과 결합하라"(2026-10-13 23:29 KST) · "1. 개발 작업 event-ctx 보완 재검토"(2026-10-13 23:4x KST) · docs/claude/event-strategy-2026-10-13.md 11절
authority: order_authority=false · 키움 호출 없음 · 정책·상태·일지·결정 파일 쓰기 없음 · 일정표는 표시·채점 전용(관문·근거·예산·수량·가격·결정과 연결 없음)
consumers: 예약 '개장 전 이벤트 점검(일정표)' v1.1(오늘 주문표 노출 줄 — CLI 호출) · score_decision_journal ticket_results(이벤트 노출별 성적) · fx-6 뒤 r-rec1 사전 등록 입력("이벤트 날 매수 보류" 여부를 우리 자료로 판정) · f-evo-loop
precondition: 없음(t1-safety 변경 파일과 겹치지 않음 — docs/claude/dev-runs/t1-safety.md 15-20행)
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 event-ctx2)
---

```dev-run
{"task_id": "event-ctx2", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 120, "builder_timeout_min": 60, "allowed_paths": ["manage-us-stock-strategy/scripts/event_calendar.py", "manage-us-stock-strategy/scripts/score_decision_journal.py", "manage-us-stock-strategy/tests/test_event_calendar.py", "manage-us-stock-strategy/tests/test_score_ticket_outcomes.py", "manage-us-stock-strategy/assets/locales/portfolio-exposure-ko-KR.json", "manage-us-stock-strategy/references/decision-journal-cards.md", "docs/claude/event-ctx2-report.md"], "target_tests": ["test_event_calendar*.py", "test_score_ticket_outcomes*.py", "test_decision_journal_cards*.py"], "commit_message": "feat(scoring): event exposure per order ticket from the official event calendar (cold path, display and scoring only)"}
```

## 목표

이벤트 대비 전략 v2의 결론은 "이벤트 날을 피하라"가 아니라 "주문표 한 장이 어떤 이벤트를 체결 전에 반영하고, 어떤 이벤트를 체결 뒤 다음 종가까지 지나는지 보이고, 결과를 기록해 우리 자료로 판정하라"이다. 자동 운영 코어(decide)는 손대지 않는다. 대신

1. 새 순수 모듈 `event_calendar.py` — 착지 시각·노출 계산, 표시 문장, 작은 읽기 전용 CLI(개장 전 점검이 부른다).
2. 채점기가 주문표마다 이벤트 노출을 **사후 계산**해 ticket_results에 붙이고 요약에 수만 센다.

일정표가 없거나 깨져도 채점의 다른 값은 한 글자도 바뀌지 않는다.

## 근거 (읽기 전용 확인 2026-10-13 23:5x KST — 줄 번호는 바뀔 수 있으니 함수 이름으로 찾는다)

- 세션 일정: `score_decision_journal.py` `load_inputs` → `run_portfolio_exposure_review.load_session_calendar(path|None, now)` → `calendar["sessions"][날짜] = {core_open_at, core_close_at(ISO, 오프셋 포함), close_type REGULAR|EARLY, session_date}`. 운영 일정(버전 2026-09-03.1)에서 2026-11-27·2026-12-24는 EARLY 13:00 ET, 2026-11-26은 세션 없음. **체결 시각 = 그 세션 core_close_at**(16:00 고정 금지).
- 주문표 필드(`load_compare_tickets`, 일지 order_ticket → `_score_ticket`): ticket_id, ticker, side("buy"|"sell", `TICKET_SIGNS`), session, mode. 채점 시작 = 주문표 세션 종가(LOC 가상 체결).
- 일정표 `docs/claude/event-calendar.json`(schema "event-calendar/1"): 최상위 `coverage_start`(2026-10-14), `horizon_end`, `allowed_source_domains`, `events[]` = {id, kind(macro_release·central_bank·earnings·election·options_expiration·market_holiday), tier(A·B·C), label(한국어), event_date(YYYY-MM-DD), time_et("HH:MM" 미국 동부 현지 또는 null), time_kst, report_date(YYYY-MM-DD 또는 null), status(VERIFIED·REPORTED·COMPUTED·NOT_ANNOUNCED), window?([시작, 끝]), source_url, result_url, ...}. 최상위 `watch`(앤트로픽 IPO 등)는 이 작업 범위 밖. 도우미 `docs/claude/event-calendar-today.py`는 읽지도 고치지도 않는다.
- 선례: 채점기 risk_1r(표시·기록 전용, `_ticket_summary`의 `risk_1r_ok`).
- 기록 모드 decide는 일지 기록 뒤 **같은 프로세스에서** `score_decision_journal.main(["--journal", …])`을 부른다(`auto_core_decide.py` `_score`, 실패·비0 종료는 `decision["journal"]["score_warning"]`만). 그래서 병합 뒤에는 decide 실행 중 채점기가 일정표를 읽는다. 결과는 채점 보고서에만 가야 하고 결정 dict·해시·일지에는 들어가면 안 된다(J-e).
- 주문표 종목 자신의 실적일은 일정표에 없다. 결정 파일 최상위 `earnings_calendar[종목]` = {status VERIFIED|NOT_ANNOUNCED|…, announcement_session, timing BEFORE_OPEN|AFTER_CLOSE(없을 수 있음), source_kind, source_url}.
- 운영 세션 일정은 2026-12-31에서 끝난다(251세션). 그 뒤 세션은 NOT_COVERED·SESSION_UNKNOWN이 정상이다.

## 바꿀 내용

### A. 새 모듈 `manage-us-stock-strategy/scripts/event_calendar.py`

순수 함수 + load 1개 + CLI. 파일·시계 접근은 load와 CLI에만.

1. `load_event_calendar(path) -> dict`: {"status": "OK"|"MISSING"|"INVALID", "sha256"(파일 바이트, 없으면 null), "coverage_start", "horizon_end", "events", "reasons"}. 예외를 밖으로 던지지 않는다. JSON 아님·schema 표지 다름·events가 목록 아님·coverage_start/horizon_end가 날짜 아님 → INVALID. 행 하나가 깨졌으면(id·kind·tier·event_date·status 빠짐·형식 오류) 그 행만 빼고 reasons에 id를 남긴다(status는 OK).
2. `landing(row) -> datetime | None` (America/New_York, zoneinfo — 서머타임 반영):
   - 제외(None): kind market_holiday·options_expiration, tier C, status NOT_ANNOUNCED.
   - time_et 있음 → event_date + time_et.
   - time_et 없음 → report_date 09:00 ET(BOJ·선거처럼 밤사이 결과, 미국 개장 전). report_date도 없으면 None("unplaced").
3. `exposure(*, session, sessions, events, coverage_start, horizon_end) -> dict` (`sessions` = 세션 일정 dict):
   - prev = session 바로 앞 세션의 core_close_at(없으면 session 날짜 00:00 ET), F = session core_close_at, F1 = 다음 세션 core_close_at, F5 = 5번째 다음 세션 core_close_at.
   - before_fill: prev < 착지 ≤ F (체결 전에 가격에 반영)
   - overnight: F < 착지 ≤ F1 (체결 뒤 다음 종가까지)
   - within_5: F < 착지 ≤ F5 (채점 5세션 구간, overnight 포함). F5가 일정 밖이면 null.
   - possible: status NOT_ANNOUNCED이고 window [s, e]가 [session 날짜, 5번째 다음 세션 날짜]와 겹치는 행(발표일 미정, 착지 계산 없음).
   - unplaced: 착지가 None인 이유가 "time_et·report_date 둘 다 없음"뿐인 행 중 event_date가 같은 범위에 드는 것.
   - own_earnings(선택 인자 `earnings`로 받은 주문표 종목의 실적 1건): {status, announcement_session, timing, position}. 착지: BEFORE_OPEN = announcement_session 09:00 ET, AFTER_CLOSE = announcement_session core_close_at + 1분, timing 없음 → position "unplaced". position = before_fill·overnight·within_5·later·unplaced 중 하나(위 경계 그대로), 실적 자료 없음 → null.
   - status: "OK"; session이 일정에 없으면 "SESSION_UNKNOWN"(목록 빈 배열); session < coverage_start이거나 F5 날짜 > horizon_end면 "NOT_COVERED"(계산 가능한 만큼 채운다).
   - 목록은 id만, 착지 시각 → id 순.
4. `exposure_line(side, exp, events) -> str` — 한국어 고정 문구는 로캘(`assets/locales/portfolio-exposure-ko-KR.json`, 새 키만 추가) 또는 `\u` 이스케이프(스크립트 ASCII):
   - buy: `이벤트(표시만): 체결 전 반영 — A·B · 체결 뒤 떠안음(다음 종가까지) — C · 발표일 미정 — E`
   - sell: `이벤트(표시만): 체결 전 반영 — A · 체결 뒤 피함(다음 종가까지) — C · 발표일 미정 — E`
   - own_earnings가 before_fill·overnight·within_5·unplaced면 끝에 ` · 자기 실적 MM/DD(장 전|장 후|시각 미정) — <체결 전 반영|밤새|5세션 안|시점 확인 필요>`.
   - A~E = 일정표 label 그대로. 빈 묶음은 생략, 한 묶음 4개 넘으면 "외 N건". 다 비면 `이벤트(표시만): 해당 없음`. NOT_COVERED → 끝에 ` · 일정표 범위 밖 — 확인 필요`. SESSION_UNKNOWN·일정표 MISSING/INVALID → `이벤트(표시만): 확인 필요(<사유 코드>)`.
5. CLI (읽기 전용, 아무 파일도 쓰지 않음, 네트워크·키움 없음):
   `python manage-us-stock-strategy/scripts/event_calendar.py --decision <decision.json> [--event-calendar <path>] [--today-et YYYY-MM-DD]`
   → stdout JSON 1개(UTF-8): {"status", "event_calendar": {status, sha256, coverage_start, horizon_end}, "decision_buy_session", "today_et", "session_match"(buy_session == today_et), "session": {"exposure", "line_buy", "line_sell"}(결정의 buy_session 기준, 주문표가 없어도), "tickets": [{ticket_id, ticker, side, mode, session, exposure, line}]}.
   - 기본 일정표 경로 = 저장소 루트/docs/claude/event-calendar.json. 세션 일정은 `load_session_calendar(None, now)`를 함수 안에서 늦게 import(채점기 `load_inputs`와 같은 방식). 테스트가 세션 일정 로더를 주입할 수 있게 한다.
   - 세션 일정 실패 → status "SESSION_CALENDAR_UNAVAILABLE" + 사유, exit 0. 결정 파일 없음·깨짐 → "DECISION_UNAVAILABLE", exit 0. 인자 오류만 exit 2. (표시 도구라 실패가 점검을 멈추지 않게.)
   - tickets = decision["tickets"] 중 dict이고 ticket_id·ticker·side·session이 비지 않은 문자열인 것. 각 주문표의 own_earnings는 같은 결정 파일의 earnings_calendar[ticker].

### B. 채점기 `score_decision_journal.py`

- 인자 `--event-calendar`(기본 저장소 루트/docs/claude/event-calendar.json). 로드 실패는 상태로만.
- `score_journal`에 선택 인자 `event_calendar`(기본 None)를 더해, ticket_results 각 행에 `"event_exposure": {"status", "before_fill", "overnight", "within_5", "possible"}`(A-3 결과의 id 목록 그대로). 세션 일정 없음 → status "SESSION_CALENDAR_UNAVAILABLE", 일정표 없음·깨짐 → "EVENT_CALENDAR_MISSING"·"EVENT_CALENDAR_INVALID", 목록은 빈 배열.
- 보고서 최상위 `"event_calendar": {status, sha256, coverage_start, horizon_end, "classification": "EX_POST_CURRENT_CALENDAR"}`. **사후 분류**다: 채점할 때의 현재 일정표로 과거 주문표를 분류한다(일정표 행이 나중에 정정되면 분류도 바뀐다). 결정 시점 표시는 개장 전 기록(workspace/outputs/pre-open, 예약 v1.1 0-1)에 남는다 — 문서 C절에도 적는다.
- own_earnings: 비교 모드 주문표는 그 주문표가 나온 decision.json의 earnings_calendar[ticker], 일지 주문표는 같은 buy_session의 decision.json(decisions_root/<날짜>/decision.json)을 찾아 쓴다. 못 찾으면 null.
- `_ticket_summary`에 `event_exposure_ok`(status OK 행 수)와 `event_overnight`(overnight가 비지 않은 행 수)만 추가. 결론 금지 규칙(MIN_SCORED_FOR_CONCLUSION)·라벨·기존 키 그대로.
- 표시: 로캘 새 키만 — 행 끝 ` · 이벤트 밤새 {ids}`(overnight가 있을 때만), 요약 끝 ` · 밤새 이벤트 노출 {n}건`. 기존 문구·키 불변.
- 이벤트 노출은 성적 값(horizons·user·would_fill·risk_1r·R 배수)에 영향 0.

### C. 문서 `references/decision-journal-cards.md`

"Scoring (read only)" 절에 3~5줄: 이벤트 노출 정의(착지 시각 대 주문표 세션 core_close_at, 매수 = 떠안음·매도 = 피함), 출처(event-calendar.json, sha256 기록), 표시·채점 전용, 코어 결정·관문·근거와 연결 없음, 결론은 기존 건수 규칙 그대로.

## 지켜야 할 것 (어기면 Judge FAIL)

1. allowed_paths 밖 변경 0. auto_core*.py·권한 경로·스키마·카드 근거 등록부·정책·일지·결정 파일·일정표·도우미를 고치지 않는다.
2. 채점 기존 값 불변: `event_exposure`·`event_calendar`·요약 2키·새 로캘 문구를 뺀 보고서가 일정표 있음·없음·깨짐 세 경우 모두 변경 전과 같다(T6 골든).
3. 일정표는 어떤 판정·관문·근거·예산·수량·가격에도 들어가지 않는다. 표시·채점 전용.
4. 새 줄에 order_authority·quantity_authority·execution_quantity·ORDER_TICKET_HUMAN_ENTRY·kill_switch를 쓰지 않는다. 새 키 이름에 stop·limit·qty·price를 쓰지 않는다.
5. 스크립트 ASCII만. 테스트는 저장소의 실제 일정표·실제 결정 파일·운영 세션 일정을 읽지 않는다(임시 파일·픽스처만).
6. 체결 시각은 세션 일정 core_close_at만 쓴다.

## 테스트 — 새 `tests/test_event_calendar.py` + `tests/test_score_ticket_outcomes.py` 갱신

- T1 착지: time_et 행 = event_date+time_et ET, time_et 없음 = report_date 09:00 ET, NOT_ANNOUNCED·tier C·휴장·옵션 만기 = None, 둘 다 없음 = None(unplaced).
- T2 노출(픽스처 세션 일정, 서머타임 경계 포함): session 2026-10-28 → FOMC(10/28 14:00) before_fill, MSFT(10/28 16:05)·GOOGL(10/28 16:30)·10/29 08:30 행 overnight, BOJ(report 10/30, time_et 없음)는 within_5지만 overnight 아님. session 2026-10-29 → BOJ overnight. session 2026-11-02 → AAPL(11/2 16:30) overnight, 선거(report 11/4) within_5. 11/1 서머타임 종료 뒤 시각이 맞는지.
- T3 조기 폐장: session 2026-11-27(core_close_at 13:00 ET) → 같은 날 14:00 ET 행은 overnight(before_fill 아님). session 2026-11-25 → 다음 세션은 11/27(11/26 휴장 건너뜀).
- T4 문장: buy "떠안음", sell "피함", 4개 초과 "외 N건", 빈 경우 "해당 없음", NOT_COVERED 끝 문구, possible 표시.
- T5 load: 없음 MISSING, JSON 아님 INVALID, schema 다름 INVALID, 행 1개 깨짐 → 그 행만 빠지고 reasons, 예외 없음.
- T6 채점 골든: 기존 채점 픽스처를 일정표 없음·있음·깨짐 세 번 → 새 키·새 문구를 뺀 보고서 동일. 있음일 때 event_exposure 목록·event_overnight 셈 확인.
- T8 자기 실적: AFTER_CLOSE가 주문표 세션 당일이면 overnight, BEFORE_OPEN이 다음 세션이면 overnight, 같은 세션 BEFORE_OPEN이면 before_fill, timing 없음이면 unplaced, 자료 없음이면 null. 매도 문장에도 붙는지.
- T7 CLI: 임시 결정 파일(주문표 buy 1·sell 1) + 임시 일정표 + 주입한 세션 일정 → JSON 구조·문장·exit 0. 결정 파일 없음 → DECISION_UNAVAILABLE exit 0. 세션 일정 실패 → SESSION_CALENDAR_UNAVAILABLE exit 0. 실행 전후 임시 폴더 내용 동일(파일 쓰기 없음).
- 실행: target_tests 패턴 + 스키마 감사 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`(스키마는 바꾸지 않지만 확인).

## 보고 — `docs/claude/event-ctx2-report.md` (한국어, 20줄 안팎)

바꾼 것, 착지·경계 규칙, T6 불변 확인 방법, **CLI 명령 그대로**(개장 전 점검 v1.1이 부를 명령), 테스트 Ran 전·후, 해석에서 갈린 부분.

## Judge 확인 항목

- J-a allowed_paths 밖 변경 0. 권한 경로·코어·일지·결정·정책·일정표 파일 무변경.
- J-b 채점 기존 값 불변(T6가 세 경우를 실제로 비교하는가). 성적 값에 이벤트 영향 0.
- J-c 착지 규칙과 경계(prev 종가 < 착지 ≤ F, F < 착지 ≤ F1, F5)가 지시대로이고, 체결 시각이 core_close_at(조기 폐장 포함)이며 서머타임 경계에서 맞는가.
- J-d 매도 문장은 "피함", 매수 문장은 "떠안음"인가.
- J-e 일정표가 판정·관문·근거·예산 어디에도 입력되지 않는가. 실패가 상태로만 남고 실행을 막지 않는가. **decide → `_score` → 채점기 경로**에서 일정표를 읽어도 결정 dict·decision_identity_hash·일지에 아무것도 들어가지 않고, 일정표 깨짐이 score_warning 말고 다른 결과를 만들지 않는가.
- J-h 자기 실적(own_earnings) 착지·경계가 지시대로이고, 실적 자료가 없을 때 null인가.
- J-f CLI가 아무 파일도 쓰지 않고, 실패 때 exit 0 + 상태, 인자 오류만 exit 2인가.
- J-g 스크립트 ASCII, 테스트가 실제 저장소 일정표·결정·운영 세션 일정을 읽지 않는가, 새 키 이름 규칙.

## loop-design-check (Cowork, 2026-10-14)

진행. 유형 = 기록 고리(주문표 → 채점 → fx-6 뒤 판정). 완료 기준 = target_tests 통과 + 기준선 대비 새 실패 0 + T6 골든. 경계 = 코어 무변경, 표시·채점만. 재시도 = 파이프라인 1회. 외부 대조 = 일정표 공식 출처 URL·sha256. 레드라인: 권한 없음, 일정표가 규칙을 바꾸지 않음, "이벤트 날 매수 보류" 같은 판정은 fx-6 뒤 사전 등록과 사용자 결정으로만.
