# score-fix Builder 보고 (2026-10-12)

지시문: docs/claude/score-fix-builder-prompt.md (결정 ext-desk-score-fix: a). 커밋·병합 없음, 작업 트리에만 남김.

## 바꾼 것
- `scripts/score_decision_journal.py`: (P1) 카드 채점 시작 세션 = 달력에서 `core_close_at` > `decision_as_of`인 첫 세션(같으면 다음). USER는 `effective_session` 마감이 `decision_as_of`보다 뒤면 그 세션(`EFFECTIVE_SESSION`), 아니면 같은 첫 세션. 행에 `decision_session`·`start_basis`·`pre_action_move` 추가. (P2) `ticket_results`·`ticket_summary`·`ticket_sources` 새 키, `score_journal(..., ticket_records=None)`, `load_compare_tickets`, `--decisions-root`(기본 workspace/outputs/auto-core). auto-core 모듈 import 없음. 일지 import는 기존 4개 + `JOURNAL_ORDER_TICKET`·`JOURNAL_TICKET_OUTCOME`.
- 로캘 새 키 4개(주문표 요약·행·구간 문구·"등급 D 참고용"). 기존 문구는 그대로. 참고 문서 채점 절에 규칙 2항목.
- 테스트: `test_decision_journal_cards.py` 기존 단언을 새 시작 세션에 맞춤(S5=SESSIONS[6] 등, 대기 테스트 평가 시각 하루 뒤로) + `StartSessionTests` 6개, 새 `test_score_ticket_outcomes.py` 11개.

## 시작가 규칙과 경계
- 시작가는 결정 뒤 첫 정규장 종가(LOC로 가장 빨리 실행할 수 있는 값)입니다. **키움 LOC 접수 마감 시각은 반영하지 않았습니다(확인 필요)**: 그날 마감 직전 접수 마감 뒤에 결정한 경우에도 같은 날 종가에서 시작합니다.
- `decision_as_of`를 읽지 못함 → `DECISION_AS_OF_INVALID`, 뒤 세션 없음 → `CALENDAR_DOES_NOT_COVER_START`.

## T1 재현 (지시문 값과 같음)
- 시작 2026-10-02, 5세션 목표 2026-10-09. MVLL pre 0.030987 / vs_cash 0.014909, NBIS 0.044438 / -0.089295, SOXL 0.064455 / -0.146371. 20·60세션 `CALENDAR_DOES_NOT_COVER_HORIZON`.

## 주문표 채점 규칙
- 자료: 일지 `order_ticket`(mode `apply`, 마지막 `ticket_outcome` = 사용자 행동) + 비교 모드 `YYYY-MM-DD/decision.json`(rerun 제외, 깨진 파일은 `ticket_sources.errors`에 파일·이유만). 일지에 있는 ticket_id는 일지 것만 채점.
- 시작 = 주문표 세션 종가. 가상 체결은 매수 종가 ≤ 상한, 매도 종가 ≥ 하한. 체결이면 `vs_no_action` = 부호 × 수익률, 미체결이면 `"0.000000"`·`NOT_FILLED_AT_CAP`. 세션 미마감이면 `PENDING`. 모든 행 등급 D, 요약 `COUNTERFACTUAL_D`, 30건 전 결론 금지. 상한·수량·주문 종류·authority 값은 출력하지 않습니다(`forbidden_keys` `[]`).

## 테스트 결과 (Ran 전 → 후)
- test_decision_journal_cards: 30 → 36 OK · test_score_ticket_outcomes: 없음 → 11 OK
- test_auto_core_decide: 69 OK (파일 수정 없음) · test_portfolio_status: 15 OK (파일 수정 없음) · 스키마 감사 PASS

## 해석에서 갈린 부분
1. `decision_session`이 달력에 없으면 기존처럼 `DECISION_SESSION_NOT_IN_CALENDAR`로 막았습니다(달력이 결정 뒤에 시작하면 시작이 늦게 잡히는 것을 막기 위해). USER의 `effective_session`이 달력에 없을 때도 같은 이유 코드입니다.
2. 미래 정보 금지를 위해 `pre_action_move`와 `start_close_vs_recorded_reference`도 평가 시각 이전에 마감한 종가만 씁니다(후자는 새 제한).
3. 가상 체결 판정은 주문표 세션의 **조정 전** 종가와 상한을 비교합니다(상한이 그날 가격 기준이므로). 수익률은 분할 조정 종가로, 사용자 평균 체결가도 같은 비율로 조정합니다.
4. 미체결 줄의 SPY 대비는 `NOT_APPLICABLE`. 사용자 `unfilled`·`not_entered`의 0은 목표 세션이 마감한 뒤에만 `SCORED`. `partial`의 값은 체결 비율로 나누지 않고 `filled_fraction`을 따로 보입니다.
5. 일지가 없음(MISSING)인데 비교 모드 주문표가 있으면 종가·달력을 읽습니다(전에는 일지 없음이면 읽지 않음). 알 수 없는 outcome 상태는 `USER_OUTCOME_INVALID`, 읽을 수 없는 상한은 `TICKET_CAP_INVALID`입니다.
6. 로캘 키는 지시문의 3줄 외에 구간 문구 키 1개를 더했습니다(기존 "현금 대비" 문구가 매도 주문표에는 맞지 않아서).
