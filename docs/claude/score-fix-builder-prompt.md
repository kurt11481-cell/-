---
id: score-fix-builder-prompt
title: 채점 시작가를 '결정 뒤 첫 실행 가능 종가'로 고치고, 자동 코어 주문표 성과 채점을 추가
date: 2026-10-12
class: 일반 변경(Cold Path 측정 코드 1개 + 테스트 + 로캘 + 참고 문서, 읽기 전용, 코어·권한 경로 불변)
source: docs/claude/external-claude-trading-desk-prompt-review-2026-10-12.md 4절·6절 · 사용자 결정 "결정 ext-desk-score-fix: a"(2026-10-12 20:04 KST) · docs/claude/automation-redesign-2026-10-10.md 125행(주문표 성과 자동 채점 계획)
authority: order_authority=false · quantity_authority=none · 키움 호출 없음 · 일지·정책·상태 파일 쓰기 없음
consumers: f-evo-loop(30건 뒤 규칙 약점 자동 발견 — 이 채점 보고서가 입력) · 관제판 ext-desk-score-fix · decide 실행이 같은 프로세스에서 부르는 채점(auto_core_decide.py `_score`, 수정하지 않음)
weekly_user_touch: 0 (병합 1번)
---

```dev-run
{"task_id": "score-fix", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 120, "builder_timeout_min": 60, "allowed_paths": ["manage-us-stock-strategy/scripts/score_decision_journal.py", "manage-us-stock-strategy/tests/test_decision_journal_cards.py", "manage-us-stock-strategy/tests/test_score_ticket_outcomes.py", "manage-us-stock-strategy/assets/locales/portfolio-exposure-ko-KR.json", "manage-us-stock-strategy/references/decision-journal-cards.md", "docs/claude/score-fix-report.md"], "target_tests": ["test_decision_journal_cards*.py", "test_score_ticket_outcomes*.py", "test_auto_core_decide*.py", "test_portfolio_status*.py"], "commit_message": "fix(scorer): start card scores at the first actionable close and score auto-core tickets vs no action"}
```

## 목표

1. (P1) 카드 결정 채점이 "결정 시점에 이미 끝난 세션의 종가"에서 시작해, 실행할 수 없던 구간(장후·밤사이·다음 세션)의 움직임이 성적에 섞인다. 시작을 **결정 시각 뒤에 마감하는 첫 세션의 종가**(시스템 기본 LOC로 가장 빨리 실행할 수 있는 값)로 바꾼다.
2. (P2) 재설계 125행이 계획한 "코어 주문표 성과 자동 채점(주문표 vs 아무것도 안 함 vs 사용자 실제 행동)"이 아직 없다. 같은 시작가 원칙으로 채점기에 추가한다. 비교 모드 주문표도 가상 결과(등급 D)로 채점해 사용자의 "켜" 판단 참고 자료를 만든다.

## 근거 (읽기 전용 확인, 2026-10-12)

- `scripts/portfolio_review_journal.py:366,384` — 카드 결정의 `decision_session` = 팩트팩 `expected_completed_us_session`.
- `scripts/score_decision_journal.py:219,158` — ANALYSIS 시작 = `decision_session` 종가.
- `scripts/portfolio_review_journal.py:432` — USER 항목은 `effective_session` 생략 시 `decision_session`.
- 코어 `ticket_outcome`은 체결 분류만(`auto_core_decide.py:11`, `auto_core_tickets.py:417`). 성과 채점 없음.
- 실측: 일지의 HOLD 3건(decision_as_of 2026-10-02T08:17:30Z, decision_session 2026-10-01)에서 첫날 움직임 +3.10%/+4.44%/+6.45%가 성적에 섞여 5세션 값이 2.8~7.3%p 다르다(아래 테스트 T1이 재현).

## 바꿀 내용

### A. 카드 채점 시작가 (P1) — `scripts/score_decision_journal.py`

1. ANALYSIS 시작 세션 = 달력에서 `core_close_at` > payload `decision_as_of`인 **첫** 세션(같으면 다음 세션 — 엄격히 큼). `decision_as_of`를 읽지 못하면 세 horizon 모두 `NOT_SCORABLE` `DECISION_AS_OF_INVALID`, 그런 세션이 달력에 없으면 `NOT_SCORABLE` `CALENDAR_DOES_NOT_COVER_START`.
2. USER 시작 세션 = `effective_session`의 `core_close_at`이 그 카드 결정의 `decision_as_of`보다 뒤면 그대로, 아니면 1번 규칙의 세션.
3. 각 결과 행에 추가: `decision_session`(원래 값), `start_basis`(`FIRST_CLOSE_AFTER_DECISION` | `EFFECTIVE_SESSION`), `pre_action_move`(decision_session 종가 → 시작 종가 수익률, 기존 6자리 문자열 형식; 둘 중 하나 없거나 그 구간이 분할 의심이면 `null`). `start_session`은 새 시작 세션이다.
4. `start_close_vs_recorded_reference`는 원래 뜻 그대로(**decision_session** 종가 − 기록된 reference_close, 같은 세션끼리의 자료 정합 확인).
5. horizon(5/20/60) 세기, "평가 시각 이전에 마감한 종가만" 규칙, 분할 검사, SPY reference only, `summary` 구조는 그대로 두고 새 시작 세션에서 센다.

### B. 코어 주문표 채점 (P2) — 같은 파일, 새 키 `ticket_results`·`ticket_summary`

- 기존 `results`(카드만)와 `summary`는 그대로 둔다. 주문표는 **별도 키**에만 넣는다(`test_auto_core_decide.py`의 `test_scorer_ignores_auto_core_entries_and_head_matches`가 `results == []`를 기대한다).
- 자료:
  1. 일지 `order_ticket` 항목(기록 모드). 같은 `ticket_id`의 `ticket_outcome` 중 마지막 항목을 사용자 실제 행동으로 쓴다.
  2. 비교 모드: `--decisions-root`(기본 `REPO_ROOT / "workspace/outputs/auto-core"`) 아래 `YYYY-MM-DD/decision.json` 파일만(`decision.rerun-*.json` 제외) 읽어 `tickets` 중 `mode == "compare"`인 것. 일지에 같은 `ticket_id`가 있으면 일지 것만 쓴다. 읽지 못한 파일은 건너뛰고 보고서 `ticket_sources.errors`에 파일 이름과 이유만 남긴다(전체 실패 아님).
  - `score_journal`에 keyword-only 인자 `ticket_records: list[dict] | None = None`을 추가한다(비교 모드 주문표 목록, 파일 읽기는 `main`/`load_inputs` 쪽). 기존 호출(인자 없이)은 일지 주문표만 채점하고 지금처럼 동작해야 한다. 종가가 없는 주문표 종목은 `load_inputs`의 `tickers`에 함께 넣어 읽는다.
- 주문표 하나의 채점(시작 세션 S = 주문표 세션):
  - S의 `core_close_at`이 평가 시각 뒤면 `PENDING`.
  - 가상 LOC 체결: 매수는 S 종가 ≤ 상한, 매도는 S 종가 ≥ 하한이면 `would_fill: true`. 상한·하한 값은 계산에만 쓰고 **출력하지 않는다**.
  - horizon 5/20/60, S에서 센다. `vs_no_action` = 체결이면 부호 × (목표 종가 / S 종가 − 1)(매수 +1, 매도 −1), 미체결이면 `"0.000000"`과 `reason: "NOT_FILLED_AT_CAP"`. SPY 대비는 카드와 같은 방식(REFERENCE_ONLY). 분할 의심·종가 없음은 카드와 같은 `NOT_SCORABLE` 규칙.
  - 사용자 실제 행동 `user`: 비교 모드 → `state: "NOT_ENTERED_COMPARE_MODE"`. 기록 모드 → `ticket_outcome` 없음 `PENDING_OUTCOME` / `filled`·`partial` → 시작가 = `average_fill_price`(없으면 S 종가), horizon별 `vs_no_action`, `filled_fraction` = 체결 수량 ÷ 주문표 수량(6자리 문자열) / `unfilled`·`not_entered` → `vs_no_action` `"0.000000"` / `changed` → `NOT_SCORABLE` `USER_CHANGED_ORDER`.
  - 행 키: `ticket_id`, `ticker`, `side`, `mode`, `session`, `start_basis: "TICKET_SESSION_CLOSE"`, `evidence_grade`(가상 체결 줄은 항상 `"D"`), `would_fill`, `horizons`, `user`. **수량·상한·주문 종류·authority 값은 넣지 않는다.**
  - `ticket_summary`: 모드별 건수, horizon별 SCORED 수, `min_scored_for_conclusion`(같은 상수 30), `conclusion_allowed`, `label: "COUNTERFACTUAL_D"`(비교 모드·가상 체결은 판단 근거가 아니라 참고).
- 출력(사람용): 로캘 `assets/locales/portfolio-exposure-ko-KR.json`에 새 메시지 키만 추가(주문표 요약 1줄 + 행 1줄 + "가상 체결은 참고용" 1줄). 기존 키 문구는 바꾸지 않는다.
- `main`: `--decisions-root` 인자 추가. 자동 코어 모듈(`auto_core*`, `reconcile_broker_state`)을 **import하지 않는다**(경로 상수는 이 파일에 둔다).

### C. 문서 — `references/decision-journal-cards.md`

채점 절에 5~8줄: 시작가 규칙(첫 실행 가능 종가, USER 규칙, pre_action_move), 주문표 채점(자료 2종, 가상 LOC 체결 규칙, 등급 D, 30건 전 결론 금지).

## 지켜야 할 것 (어기면 Judge FAIL 또는 파이프라인 권한 상승)

1. 권한 경로 파일(`auto_core*.py`, `test_auto_core*.py`, `portfolio_exposure.py` 등 `tools/dev_pipeline/authority-paths.txt`)은 읽기·실행만 한다.
2. 기존 줄 중 `order_authority`·`quantity_authority`·`execution_quantity`가 들어 있는 줄은 지우거나 바꾸지 않는다. 새 줄에 이 세 단어와 `ORDER_TICKET_HUMAN_ENTRY`, `kill_switch`를 쓰지 않는다(일지 payload의 `authority` 값을 복사하지 않는다).
3. 스크립트는 ASCII만(`ScriptHygieneTests`). 일지·상태·정책 파일 쓰기 없음. `portfolio_review_journal`에서 import하는 이름은 기존 4개 + `JOURNAL_ORDER_TICKET`·`JOURNAL_TICKET_OUTCOME` 두 상수만 — `test_the_scorer_has_no_code_path_that_writes_the_journal`의 기대 집합을 이 두 이름만큼만 늘린다. 쓰기 함수 이름 금지 검사는 그대로 통과해야 한다.
4. 보고서 전체가 `validate_holding_card.forbidden_keys` 검사에서 `[]`이어야 한다(예: `limit_price`, `order_type`, `buy_qty`, `sell_price`류 키 금지).
5. `report["journal"]["head_sha256"]`와 `portfolio_status.journal_pending` 동작 불변. `score_journal`은 계속 파일을 읽지 않는 순수 함수.
6. 미래 정보 금지: 평가 시각 이전에 마감한 세션 종가만 쓴다. 30건 미만이면 `conclusion_allowed: false`.

## 테스트 — 새 파일 `tests/test_score_ticket_outcomes.py` + `tests/test_decision_journal_cards.py` 갱신

기존 테스트가 옛 시작 세션을 기대하면 새 규칙에 맞게 고친다(테스트 수를 줄이지 않는다). 새 테스트(표준 라이브러리, 기존 fixture 도우미 재사용 가능):

- T1 실측 재현: 달력 2026-10-01~10-09(10/3·10/4 주말 제외, 각 세션 `core_close_at` 20:00Z), decision_as_of `2026-10-02T08:17:30.605734+00:00`, decision_session 2026-10-01, HOLD 3건, 종가(세션 10-01, 10-02, 10-05, 10-06, 10-07, 10-08, 10-09):
  - MVLL 36.7900, 37.9300, 37.6500, 42.0300, 41.3800, 38.3600, 38.4955
  - NBIS 232.4600, 242.7900, 232.5800, 249.8900, 237.1500, 219.8100, 221.1100
  - SOXL 153.7500, 163.6600, 164.2200, 164.2100, 158.8700, 142.4700, 139.7050
  - 평가 시각 2026-10-10T00:00Z → 시작 2026-10-02, `pre_action_move` MVLL `0.030987`, NBIS `0.044438`, SOXL `0.064455`; 5세션 목표 2026-10-09, `vs_cash` MVLL `0.014909`, NBIS `-0.089295`, SOXL `-0.146371`; 20·60세션은 달력 범위 밖 `NOT_SCORABLE`.
- T2 decision_as_of가 정규장 마감 전(같은 날 15:00Z) → 같은 날 세션 시작. T3 decision_as_of == 그날 `core_close_at` → 다음 세션.
- T4 USER: `effective_session` == decision_session → 규칙 세션, `start_basis` `FIRST_CLOSE_AFTER_DECISION`; 그 뒤 세션이면 그대로 `EFFECTIVE_SESSION`.
- T5 decision_session→시작 구간 분할 의심 → `pre_action_move` null, 기존 분할 규칙 유지.
- T6 매수 주문표: 상한 ≥ S 종가 → `would_fill` true, 값 = 수익률 / 상한 < S 종가 → false, `"0.000000"`, `NOT_FILLED_AT_CAP`. T7 매도 주문표 체결 규칙과 부호.
- T8 S가 평가 시각 뒤에 마감 → `PENDING`.
- T9 비교 모드 파일: rerun 파일 무시, 깨진 JSON은 `ticket_sources.errors`에 남고 나머지는 채점, 일지와 같은 `ticket_id`는 일지 것만(중복 없음).
- T10 사용자 결과: filled(평균 체결가 시작) / partial(`filled_fraction`) / unfilled → 0 / changed → `USER_CHANGED_ORDER` / 결과 없음 → `PENDING_OUTCOME` / 비교 모드 → `NOT_ENTERED_COMPARE_MODE`.
- T11 보고서 `forbidden_keys == []`, `ticket_results` 어디에도 주문표의 상한 숫자·수량 숫자 키가 없음.
- T12 `score_journal`을 `ticket_records` 없이 부르는 기존 형태가 그대로 동작.
- 실행: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_score_ticket_outcomes*.py"`, `-p "test_decision_journal_cards*.py"`, `-p "test_auto_core_decide*.py"`(고치지 않고 통과만 확인), `-p "test_portfolio_status*.py"`.

## 보고 — `docs/claude/score-fix-report.md` (한국어, 20줄 안팎)

바꾼 것, 시작가 규칙과 경계(키움 LOC 접수 마감 시각은 반영하지 않음 — 확인 필요로 적기), T1 재현 값, 주문표 채점 규칙, 테스트 결과(Ran 수 전·후), 해석에서 갈린 부분.

## Judge 확인 항목

- J-a 허용 경로 6개 외 변경이 없고 권한 경로 파일(특히 `auto_core*.py`, `test_auto_core*.py`)이 그대로인가.
- J-b ANALYSIS 시작 세션이 `core_close_at > decision_as_of`인 첫 세션이고(같으면 다음), USER 규칙·`pre_action_move`·`start_close_vs_recorded_reference`(decision_session 기준) 의미가 지시대로인가. T1 값이 지시문 값과 같은가.
- J-c 평가 시각 뒤 종가를 쓰는 경로가 없는가(카드·주문표·사용자 결과 모두).
- J-d 주문표 결과가 `results`가 아닌 `ticket_results`에만 있고, 기존 `score_journal` 호출이 그대로 동작하며 `journal_pending`이 CURRENT로 남는가.
- J-e 가상 LOC 체결 규칙(매수 ≤, 매도 ≥)과 부호, 미체결 0, 사용자 결과 상태별 처리가 맞는가. 비교 모드 줄이 등급 D·`COUNTERFACTUAL_D`로 표시되는가.
- J-f 출력에 수량·상한·주문 종류·authority 값이 없고 `forbidden_keys`가 `[]`인가. 스크립트 ASCII, 일지 쓰기 경로 없음, import 집합이 지시대로인가.
- J-g 비교 모드 파일 읽기가 rerun 파일을 무시하고, 깨진 파일 하나가 전체를 멈추지 않으며, 일지와 중복된 ticket_id를 두 번 세지 않는가.
