---
id: risk1r2-builder-prompt
title: 자동 코어 매수 주문표에 1R(무효선까지 손실) 표시·기록 + 채점기 R 배수
date: 2026-10-12
class: 권한 경로를 건드리는 표시·기록 변경(dev-run class authority — 경로 때문. 의미상 권한·한도·주문 단계·수량·가격·관문 불변)
source: docs/claude/external-traders-handbook-ftd-pullback-review-2026-10-12.md 3절 4번·6절 · 사용자 결정 "결정 ext-1012-setup: B"(2026-10-12 20:47 KST) · manage-us-stock-strategy/references/trade-timing-validation.md "Stop and invalidation"(20EMA − 0.75 ATR)
precondition: score-fix 병합 뒤에만 큐에 넣는다(score_decision_journal.py의 ticket_results를 확장하므로) — 충족(d70aac2)
rerun_of: risk1r — 1차 실행이 PC 재부팅으로 중단(dev-queue 로그 2026-10-12T12:00:06Z "DEV-RUN start risk1r" 뒤 종료 기록 없음, Builder 파일 변경 0). 같은 id는 preflight가 막으므로 새 id. 내용은 1차 지시문과 같다
authority: order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음 · 주문표의 수량·가격·관문 결과 불변
consumers: 사용자(주문표 화면·알림 줄) · 결정 일지 order_ticket(계획 R 기록) · score_decision_journal ticket_results(R 배수) · f-evo-loop(30건 뒤 "무효선에서 멀리 산 주문이 더 나빴나", 진입 근거 종류별 R 성적)
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 risk1r2 -ApproveAuthority — 경로 때문에 붙는 플래그, 사용자 결정 B 있음)
---

```dev-run
{"task_id": "risk1r2", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 140, "builder_timeout_min": 75, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_tickets.py", "manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/scripts/portfolio_review_journal.py", "manage-us-stock-strategy/scripts/score_decision_journal.py", "manage-us-stock-strategy/schemas/auto-core-ticket.schema.json", "manage-us-stock-strategy/schemas/auto-core-decision.schema.json", "manage-us-stock-strategy/schemas/portfolio-review-journal-payload.schema.json", "manage-us-stock-strategy/tests/test_auto_core_risk1r.py", "manage-us-stock-strategy/tests/test_auto_core_tickets.py", "manage-us-stock-strategy/tests/test_auto_core_decide.py", "manage-us-stock-strategy/tests/test_score_ticket_outcomes.py", "manage-us-stock-strategy/tests/test_portfolio_review_journal.py", "manage-us-stock-strategy/assets/locales/portfolio-exposure-ko-KR.json", "manage-us-stock-strategy/references/decision-journal-cards.md", "docs/claude/risk1r2-report.md"], "target_tests": ["test_auto_core_risk1r*.py", "test_auto_core_tickets*.py", "test_auto_core_decide*.py", "test_score_ticket_outcomes*.py", "test_portfolio_review_journal*.py", "test_decision_journal_cards*.py"], "commit_message": "feat(auto-core): display-only 1R (EMA20 - 0.75 ATR invalidation) on buy tickets, journal and ticket scoring"}
```

## 목표

매수 주문표 한 장마다 "근거가 틀렸다고 볼 가격(무효선)까지 내려가면 계좌가 몇 % 줄어드는지"(1R)를 계산해 **보여 주고 기록만** 한다. 수량·가격·관문·차단·재발행·결정 키는 한 글자도 바뀌지 않는다. 손절·매도·관문과 연결하지 않는다.

이유(검토 메모 6절, D): 같은 종목·같은 금액 주문이라도 무효선까지 거리가 최근 1년 하위10%↔상위10% 사이 5~14배 다르다. 지금 코어는 이 차이를 보지 못한다. 주문 때 계획 R을 기록해 두어야 채점기가 R 배수로 성적을 낼 수 있다.

## 근거 (읽기 전용 확인, 2026-10-12, base e49bc35 + score-fix)

- `auto_core_rules.py:245-261` — 종목별 `indicators`(평가 세션 t)에 `ema20`·`atr14`(Wilder)·`sigma60`이 이미 있다.
- `auto_core_decide.py:914-915` — ctx에 `closes`·`sigmas`만 넘긴다(지표 전체는 `symbols_out[...]["indicators"]`).
- `auto_core_tickets.py:785` `_buy_ticket` — 기준가 `reference`, `sigma`, 최종 `qty`, `ctx["equity"]`. `:708` `_common_ticket`이 주문표 dict를 만든다.
- `auto_core_decide.py:957` `_dashboard` — runCore.tickets(비교·기록 모드), orders(기록 모드, `evidence` 문자열을 화면이 표시 — docs/claude/dashboard-order-panel-2026-10-07.md 38행), `:313` TICKET 알림 줄(기록 모드).
- `portfolio_review_journal.py:569` `auto_core_payloads` — order_ticket payload는 고른 키만 복사(지금 근거 종류 없음).
- `schemas/auto-core-ticket.schema.json` — `additionalProperties: false`.

## 바꿀 내용

### A. 계산 — `auto_core_tickets.py`

1. 상수 표 `S`에 `"R1_ATR_MULT": (Decimal("0.75"), "trade-timing-validation.md Stop and invalidation: 20EMA - 0.75 ATR14; display-only 1R (user decision ext-1012-setup B, 2026-10-12)")`.
2. 순수 함수 `risk_1r(reference, ema20, atr14, sigma, qty, equity) -> dict` (Decimal 계산):
   - 입력 중 하나라도 None이면 `{"status": "unk", "reason": "INDICATOR_MISSING", ...나머지 null}`.
   - `invalidation` = ema20 − 0.75 × atr14, 센트 내림(ROUND_FLOOR). `per_share` = reference − invalidation.
   - per_share ≤ 0 → `{"status": "below_band", "invalidation": ..., 나머지 null}`.
   - 아니면 `status "ok"`, `r_pct` = per_share ÷ reference(6자리 문자열, 반올림 ROUND_HALF_UP), `r_sigma` = r_pct ÷ sigma(2자리 문자열), `loss_usd` = qty × per_share(센트), `loss_pct_equity` = loss_usd ÷ equity(6자리 문자열).
   - 항상 `"basis": "EMA20-0.75xATR14@evaluation_session"`, `"grade": "D"`, `"display_only": true`.
3. `_buy_ticket`에서 **최종 qty가 정해지고 주문표가 만들어진 뒤에만** `ticket["risk_1r"] = risk_1r(...)`. ctx에 지표가 필요하면 `auto_core_decide.py`가 ctx에 `"indicators": {symbol: {"ema20":…, "atr14":…}}`만 추가(기존 키 불변). 매도 주문표에는 넣지 않는다.
4. 표시 문장(한국어는 `\u` 이스케이프 — 스크립트 ASCII 유지): ok `"1R(표시만) 무효선 $X · 기준가 대비 -Y% (Zσ) · 약 $L = 자산 W% · 자동 매도 없음"`, below_band `"1R(표시만) 기준가가 무효선 $X 아래 — 셋업 없음"`, unk `"1R 확인 필요(지표 없음)"`. `ticket["risk_1r"]["line"]`에 둔다.

### B. 표시 — `auto_core_decide.py`

- runCore.tickets 항목에 `"risk1r": <line 또는 None>` 추가.
- 기록 모드 orders 항목의 `evidence` 문자열 끝에 `" · " + line`(매수만). 기록 모드 TICKET 알림 줄 끝에 `" · 1R 자산 W%"`(ok일 때만).
- 결정 스키마가 runCore.tickets 키를 막으면 `risk1r`(string|null)만 추가.

### C. 기록 — `portfolio_review_journal.py` + `portfolio-review-journal-payload.schema.json`

- order_ticket payload에 `"risk_1r": {status, invalidation, r_pct, r_sigma, loss_pct_equity, grade}`(매수만, 매도는 키 없음)와 `"evidence_weak_kinds": [...]`(주문표 `evidence.weak` 그대로) 추가. 기존 키·값·순서 의미 불변. 스키마에 두 키를 선택 속성으로 추가.

### D. 채점 — `score_decision_journal.py` (score-fix의 ticket_results 확장)

- 주문표 행에 `risk_1r`(status, r_pct, r_sigma)와 `evidence_weak_kinds`를 자료에서 그대로 복사(일지 payload 또는 비교 모드 decision.json 주문표; 없으면 null).
- horizon마다 `r_multiple` = `vs_no_action` ÷ r_pct(6자리 문자열). 조건: 매수·`would_fill` true(또는 사용자 체결)·risk_1r status ok·vs_no_action 존재. 아니면 null. 미래 정보 금지 규칙은 score-fix 그대로.
- `ticket_summary`에 `risk_1r_ok`(건수)만 추가. 30건 전 결론 금지(`conclusion_allowed` 규칙 그대로).
- 로캘에 새 키만 추가(행 끝 "R 배수 …" 1줄). 기존 문구 불변. 보고서 `forbidden_keys == []` 유지(새 키 이름에 stop·limit·qty·price 류를 쓰지 않는다).

### E. 문서 — `references/decision-journal-cards.md`

주문표 채점 절에 3~5줄: 1R 정의(표시·기록 전용, 등급 D, 매도·관문 연결 없음), r_multiple 계산 조건.

## 지켜야 할 것 (어기면 Judge FAIL)

1. 주문표의 `qty`, `price`, `priceRule`, `priceCalc`, `amount`, `gates`, `regret`, `decision_key`, `reason`, `evidence`(dict), `blocked` 목록, `no_action`, 재발행 장부 값이 변경 전과 **완전히 같다**. 1R 계산 실패가 주문표를 막거나 FAIL로 만들지 않는다(unk로 표시만).
2. 기존 줄 중 `order_authority`·`quantity_authority`·`execution_quantity`가 들어 있는 줄을 지우거나 바꾸지 않는다. 새 줄에 이 세 단어와 `ORDER_TICKET_HUMAN_ENTRY`, `kill_switch`를 쓰지 않는다. `"stop"`이라는 단어를 새 키·문구에 쓰지 않는다("무효선").
3. 스크립트 ASCII만. Claude Code 설정상 "auto_core.py"가 들어간 명령은 거부되므로 테스트는 `-p "test_auto_core*.py"` 패턴으로만 돌린다.
4. 비교 모드에서도 계산·표시된다(주문표 "비교 중" 표지 불변).

## 테스트 — 새 파일 `tests/test_auto_core_risk1r.py` + 기존 파일 갱신

- T1 산식: reference 100.00, ema20 98.00, atr14 4.00, sigma 0.025, qty 10, equity 10000 → invalidation 95.00, r_pct "0.050000", r_sigma "2.00", loss_usd 50.00, loss_pct_equity "0.005000", line에 "-5.0%"·"2.0σ"·"$50"·"0.50%" 포함.
- T2 below_band: reference 94.00(같은 지표) → status below_band, r_pct·loss 필드 null.
- T3 지표 없음 → unk, 주문표는 그대로 발행.
- T4 불변: 기존 `test_auto_core_tickets`·`test_auto_core_decide` 픽스처로 만든 주문표에서 `risk_1r` 키를 빼면 변경 전 결과와 dict가 같다(golden 비교). 차단 목록도 같다.
- T5 매도 주문표에는 `risk_1r` 없음.
- T6 스키마: 주문표·결정·일지 payload 스키마 검증 통과(risk_1r 있음/없음 모두).
- T7 표시: runCore.tickets[].risk1r, 기록 모드 orders evidence 끝, TICKET 알림 줄 끝 문구.
- T8 일지 payload에 risk_1r·evidence_weak_kinds, 매도 payload엔 risk_1r 없음.
- T9 채점: 체결 매수 r_pct "0.050000", vs_no_action "0.100000" → r_multiple "2.000000". 미체결·below_band·unk·매도 → null. forbidden_keys [].
- 실행: target_tests 6개 패턴 + 스키마 감사 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`.

## 보고 — `docs/claude/risk1r2-report.md` (한국어, 20줄 안팎)

바꾼 것, 산식·반올림, 불변 확인 방법(T4), 표시 위치(비교 모드 화면 반영은 대시보드 HTML이 runCore.tickets[].risk1r을 읽어야 함 — 확인 필요로 적기), 테스트 Ran 전·후, 해석에서 갈린 부분.

## Judge 확인 항목

- J-a 허용 경로 외 변경 없음. 권한·한도·주문 단계·제품 승인·대조 불변식·kill switch 관련 코드 경로와 값이 그대로인가.
- J-b 주문표의 수량·가격·관문·차단·결정 키·재발행 장부가 변경 전과 같은가(T4가 실제로 비교하는가).
- J-c 산식(EMA20 − 0.75×ATR14, 평가 세션 t, 센트 내림)과 상태 3가지, 문자열 자릿수가 지시대로인가. 1R 실패가 주문표를 막지 않는가.
- J-d 1R이 매도·관문·근거 강도·예산 어디에도 입력되지 않는가(표시·기록 전용). "stop" 단어·권한 단어가 새 줄에 없는가.
- J-e 일지 payload·스키마 변경이 선택 속성 추가뿐이고 기존 키 의미가 같은가. 매도 payload에 risk_1r이 없는가.
- J-f r_multiple이 지시한 조건에서만 계산되고 평가 시각 뒤 종가를 쓰지 않는가. forbidden_keys [] 유지.
- J-g 스크립트 ASCII, 비교 모드에서도 계산·표시되는가.
