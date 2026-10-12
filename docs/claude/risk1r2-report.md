# risk1r2 Builder 보고 (2026-10-12)

## 바꾼 것
- `auto_core_tickets.py`: 상수 `R1_ATR_MULT`(0.75, 출처 trade-timing-validation.md) + 순수 함수 `risk_1r()`, `risk_1r_share_text()`. `_buy_ticket`이 최종 qty로 주문표를 다 만든 **뒤** `ticket["risk_1r"]`만 붙인다(계산 예외는 `unk`/`CALC_FAILED`, 주문표는 그대로). 매도 주문표엔 없음.
- `auto_core_decide.py`: ctx에 `indicators`(종목별 ema20·atr14, 평가 세션 t)만 추가. runCore.tickets[].`risk1r`(줄 또는 null), 기록 모드 orders `evidence` 끝 `" · " + 줄`(매수만), TICKET 알림 끝 `" · 1R 자산 W%"`(ok만).
- `portfolio_review_journal.py` + payload 스키마: order_ticket에 선택 키 `risk_1r`{status, invalidation, r_pct, r_sigma, loss_pct_equity, grade}(매수만), `evidence_weak_kinds`(evidence.weak 그대로, 매수·매도). 자동 코어 항목 검사는 "필수 키 전부 + 선택 키 2개까지"로 넓힘(기존 항목은 그대로 읽힘, 모르는 키는 여전히 PAYLOAD_FIELDS_INVALID).
- `score_decision_journal.py`: 행에 `risk_1r`(status, r_pct, r_sigma), `evidence_weak_kinds`; horizon마다 `r_multiple`; `ticket_summary.risk_1r_ok`. 로캘 키 `score_ticket_r_multiple` 1개 추가(매수·ok 행 끝). 문서 `decision-journal-cards.md` 6줄.
- 결정 스키마는 runCore가 자유 객체라 고치지 않음.

## 산식·반올림
- 무효선 = EMA20 − 0.75×ATR14 → 센트 내림. per_share = 기준가 − 무효선. ≤0 → `below_band`(무효선만). 입력 None/NaN → `unk`(INDICATOR_MISSING), sigma≤0 등 → `unk`(INDICATOR_INVALID).
- r_pct = per_share÷기준가(6자리 HALF_UP), r_sigma = r_pct÷sigma(2자리 HALF_UP), loss_usd = qty×per_share(센트), loss_pct_equity = loss_usd÷equity(6자리).
- 표시 줄의 Y·Z·W·L은 기록된 반올림 값에서 만든다(화면=기록). r_multiple = vs_no_action÷r_pct(채점기 `_text`, 6자리).

## 불변 확인(T4)
- 바꾸기 전(base 5ed21b4)에 기존 픽스처 8개(Scenario 기본·G2b·현금5·리서치 막힘·매도·PWR, decide 비교·기록)의 tickets(risk_1r 제외)·blocked·no_action·candidates(decide는 keys)를 canonical sha256으로 재서 `GOLDEN`에 고정. 변경 뒤 같은 해시 + 매수 주문표 4건 이상이 실제로 ok/below_band 1R을 가짐을 함께 확인.

## 표시 위치
- 비교 모드: runCore.tickets[].risk1r에만 실림. **대시보드 HTML이 이 필드를 읽는지는 확인 필요**(이번 범위 밖).
- 기록 모드: 주문 패널 evidence 문자열 끝, TICKET 알림 줄 끝.

## 테스트 (Ran 전 → 후)
- test_auto_core_risk1r 0 → 17(새 파일) · test_auto_core_tickets 60 → 60 · test_auto_core_decide 69 → 69 · test_score_ticket_outcomes 11 → 11 · test_portfolio_review_journal 14 → 14 · test_decision_journal_cards 36 → 36 (기존 파일엔 단언만 추가, 메서드 수 불변이라 "전"은 같은 수). test_auto_core* 전체 304 OK(skip 1, 기존). 스키마 감사 PASS.

## 해석에서 갈린 부분
- invalidation·loss_usd는 문자열("95.00")로 둠(주문표·일지 같은 형식, r_pct와 같은 방식). r_sigma는 지시 그대로 반올림된 r_pct÷sigma.
- `evidence_weak_kinds`는 매도 payload에도 넣음(지시 C는 risk_1r만 매수 한정).
- r_multiple은 가상 체결(would_fill true) horizons와 사용자 filled/partial horizons 양쪽에 붙임. risk_1r_ok는 기록된 status ok 행 수.
- decision_sha256에 risk_1r이 포함되므로, 병합 당일 옛 코드가 이미 기록한 같은 평가 세션을 새 코드로 재실행하면 R2-5에 따라 CORE_DECISION_ALREADY_RECORDED_DIFFERENT(HOLD)가 한 번 날 수 있음.
