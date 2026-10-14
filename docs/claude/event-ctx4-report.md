# event-ctx4 Builder 보고 (2026-10-14)

**바꾼 것**
- 새 `manage-us-stock-strategy/scripts/event_calendar.py`(ASCII, 순수 함수 + `load_event_calendar` + 읽기 전용 CLI). 한국어 문구는 로캘 새 키(`event_*`, `score_ticket_event_*`)에만 있음.
- `score_decision_journal.py`: `--event-calendar`(기본 docs/claude/event-calendar.json), `score_journal(event_calendar=None, decision_earnings=None)`, ticket_results 각 행 `event_exposure`, 보고서 최상위 `event_calendar`(sha256·`classification=EX_POST_CURRENT_CALENDAR`), `ticket_summary`에 `event_exposure_ok`·`event_overnight`만 추가. `load_compare_tickets`가 결정 파일의 `earnings_calendar`를 주문표 id별·buy_session별로 함께 돌려줌.
- `references/decision-journal-cards.md` Scoring 절에 이벤트 노출 정의·사후 분류·표시 전용 bullet 1개와 사용법 줄 인자 추가.

**착지·경계 규칙**: 착지 = event_date+time_et(ET, zoneinfo 서머타임) / time_et 없으면 report_date 09:00 ET / 둘 다 없으면 None(unplaced). market_holiday·options_expiration·tier C·NOT_ANNOUNCED 제외. 체결 시각 F = 세션 일정 `core_close_at`(조기 폐장 13:00 포함). before_fill: prev 종가 < 착지 ≤ F, overnight: F < 착지 ≤ F1, within_5: F < 착지 ≤ F5(F5 없으면 null). 자기 실적: BEFORE_OPEN = 발표 세션 09:00 ET, AFTER_CLOSE = 발표 세션 core_close_at + 1분.

**T6 불변 확인**: 같은 픽스처(주문표 6건·사용자 결과·SPY)를 ① 인자 없이(변경 전 호출 형태) ② 일정표 없음 ③ 있음 ④ 깨짐으로 채점 → `event_calendar`·`event_exposure`·요약 2키를 뺀 보고서 JSON이 넷 모두 같고, `render_report` 줄에서 새 문구 3종을 정규식으로 지운 결과도 같음. CLI(`main`)로도 있음·깨짐 두 보고서 비교.

**CLI 명령 그대로**(개장 전 점검 v1.1):
`python manage-us-stock-strategy/scripts/event_calendar.py --decision workspace/outputs/auto-core/LATEST_DECISION.json`
(선택 `--event-calendar <path>` `--today-et YYYY-MM-DD`; stdout JSON 1개, 파일 쓰기 없음, 실패도 exit 0 + status, 인자 오류만 exit 2)

**테스트 Ran 전 → 후**: test_score_ticket_outcomes 11 → 14 OK, test_event_calendar 0 → 16 OK(수정 1회차 뒤 18 OK), test_decision_journal_cards 36 → 36 OK. 추가 확인: test_auto_core* 383 OK(skip 1, decide→_score→채점기 경로 포함), 스키마 감사 PASS.

**해석에서 갈린 부분**
1. `own_earnings`는 `event_exposure` 안 6번째 키로 넣음(B절 목록 5키 + A-3 own_earnings). position에 `earlier`(착지 ≤ prev)를 더하고, F1/F5가 세션 일정 밖이면 `unplaced`. timing 없는 실적(수정 1회차, Judge min_fixes): 발표일이 직전 세션 날짜보다 앞이면 earlier(주문표 세션이 일정 첫 세션이면 세션 날짜와 비교), 5번째 다음 세션 날짜 뒤면 later, 그 밖(직전 세션 날짜 당일, 직전 세션과 주문표 세션 사이 휴장일 포함)은 모두 unplaced(지시문 A-3 "timing 없음 → unplaced").
2. F5가 세션 일정 밖(운영 일정 12/31 끝)이어도 NOT_COVERED로 둠(범위 확인 불가 = 확인 필요).
3. possible·unplaced에도 착지 제외 규칙(휴장·옵션 만기·tier C)을 똑같이 적용. 같은 id 중복 행은 뒤 행을 빼고 reasons에 남김.
4. 보고서 `event_calendar`에 `reasons`(빠진 행)도 넣음. 일정표가 OK가 아니면 요약 줄 끝에 ` · 이벤트 노출 확인 필요(<status>)`(새 키 `score_ticket_event_unavailable`) — 없는 자료를 보이게 하려는 것.
5. 일지 주문표의 자기 실적: 같은 ticket_id를 가진 decision.json을 먼저, 없으면 같은 buy_session의 decision.json(뒤 폴더 우선). 비교 주문표는 그 id가 처음 나온 파일.
6. CLI 최상위 status에 `EVENT_CALENDAR_MISSING`·`_INVALID`도 둠(exit 0). 세션 일정 없음이 일정표 상태보다 먼저.
7. 기존 테스트 2곳 수정: 행 키 정확 집합에 `event_exposure` 추가, 기존 CLI 테스트에 임시 `--event-calendar` 전달(실제 일정표 안 읽게). allowed_paths 밖인 test_decision_journal_cards의 ScoreLocationTests는 기본 경로로 저장소 일정표를 읽기만 함(단언은 일정표와 무관).
8. 실제 파일로 CLI를 한 번 돌려 보는 확인은 이 세션 권한에서 거부되어 하지 못함(T7 임시 파일 테스트로만 확인).
