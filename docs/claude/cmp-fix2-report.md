---
id: cmp-fix2-report
title: cmp-fix2 Builder 보고 — 사건형 트리거 B2 여유를 충족일에서, 종목 상한 집합을 종목 코드로
date: 2026-10-13
prompt: docs/claude/cmp-fix2-builder-prompt.md
authority: order_authority=false · 판정·주문표·관문·알림·일지 내용 불변 · 키움 호출 없음 · 정책·상태 파일 변경 없음
---

# cmp-fix2 Builder 보고

## 바꾼 파일 (allowed_paths 안)

| 파일 | 내용 |
|---|---|
| `manage-us-stock-strategy/scripts/auto_core_rules.py` | 결함 1 (여유 계산) |
| `manage-us-stock-strategy/scripts/auto_core_compare.py` | 결함 2 (상한 집합 비교) |
| `manage-us-stock-strategy/tests/test_auto_core_compare_fix.py` | 새 테스트 12개 |
| `docs/claude/cmp-fix2-report.md` | 이 보고 |

기존 테스트 파일은 고치지 않았다. 고친 두 스크립트는 CRLF·ASCII 그대로다.

## 결함 1 — `auto_core_rules.py`

- 113행 `EVENT_MARGIN_GROUPS` (새 상수, 표시 전용): `overheat_fade`·`oversold_rebound`(C2), `false_breakout`·`false_breakdown`(C4), `rebound_fail`·`pullback_rebound`(C6). C7 그룹(`good_news_drop`·`bad_news_rise`)은 넣지 않았다(연구 기록 그룹, 지시대로).
- 398행 `_event_day(raw, opposite, index)` (새 함수): `_event_state(raw, opposite, index)`가 `"hit"`일 때만, 같은 창(`EVENT_WINDOW_SESSIONS` = 5) 안의 마지막 raw True 세션 = `fired[-1]`을 돌려준다. hit가 아니면(none·unk, 반대 쪽이 그 뒤에 발생해 해소된 경우 포함) `None`. 창과 반대 쪽 해소 규칙은 `_event_state`를 그대로 불러 쓰므로 판정과 어긋날 수 없다. `_event_state` 자체는 고치지 않았다.
- `evaluate_symbol`:
  - 전에 `indicator_row` 바로 뒤(옛 535행)에서 하던 `result["margins"] = group_margins(series, c8)`를 지우고, 트리거·그룹 계산이 끝난 뒤(630행) `group_margins(series, c8, event_days)`로 옮겼다. `result` 딕셔너리에 `margins` 키가 들어가는 순서는 그대로다(앞의 키들은 모두 처음부터 있던 키).
  - 570행 내부 함수 `note_event_day`: 그룹이 `EVENT_MARGIN_GROUPS`에 있고 그 트리거의 오늘 상태가 `"hit"`일 때만 `_event_day(values, 반대 쪽, t)`를 기록한다. 공통 규칙(611행)과 카드 별칭(627행) 둘 다 같은 함수를 쓴다. 한 그룹에 hit 기여자가 둘 이상이면 가장 늦은 충족일을 쓴다(현재 공통 규칙과 이를 대신하는 카드 별칭은 한 그룹에 동시에 있지 않으므로 실제로는 하나뿐).
  - 상태(state)·previous_state·new·groups·triggers 계산 줄은 바꾸지 않았다. `event_days`는 `group_margins`에만 들어간다.
- 638행 `group_margins(series, c8, event_days=None)`: 먼저 마지막 세션 t의 값을 모두 계산하고(변경 전과 같은 식), `event_days`에 있는 사건형 그룹만 그 충족일 값으로 덮어쓴다. `EVENT_MARGIN_GROUPS` 밖의 그룹 이름이 들어와도 무시한다.
- 650행 `_margins_at(series, c8, t)`: 변경 전 `group_margins` 본문을 그대로 옮기고 인덱스만 인자로 받는다. 따라서 충족일 d에서의 값은 "그날 결정 수치·선 ÷ 그날 종가"다.
  - false_breakout / false_breakdown: |종가[d] − 20세션 종가 고점/저점[d−1]| ÷ 종가[d] (C4 판정의 선과 같음)
  - rebound_fail / pullback_rebound: |종가[d] − EMA20[d]| ÷ 종가[d]
  - overheat_fade / oversold_rebound: |고가[d] 또는 저가[d] − (EMA20[d−1] ± 2.5×ATR14[d−1])| ÷ 종가[d]
- 결과 형식은 그대로 `result["margins"][group]` 한 값(float|None). 결정 기록 스키마·키 이름 변경 없음. 스키마 감사 PASS.

### 카드 별칭 처리

처리했다. 카드 트리거 중 `rule_kind == "event"`인 것(`pullback_rebound`, `good_news_drop`)도 같은 `note_event_day`를 거친다. `pullback_rebound` 카드의 값 배열(`card_raw`)은 공통 C6+ 배열과 같고, 반대 쪽은 판정과 똑같이 `common[opposite[replaces]]`(C6−)를 쓴다. `good_news_drop`은 `EVENT_MARGIN_GROUPS` 밖이라 그대로다. 테스트 `test_card_alias_of_an_event_rule_uses_its_firing_session`이 공통 규칙과 카드 별칭(U6) 둘 다 같은 충족일 여유가 되는지 확인한다.

## 결함 2 — `auto_core_compare.py`

- 61행 `CAP_TICKER = re.compile(r"^\s*([A-Z][A-Z0-9.]{0,9})\b")` (지시문의 식 그대로).
- 121행 `_caps_category(core_caps, llm_caps, timing)` (새 함수), 232행에서 호출:
  1. 문자열 목록이 그대로 같으면 B1 `SAME` (변경 전과 같음, 빈 목록끼리 포함).
  2. LLM 항목 중 하나라도 종목 코드를 못 뽑으면(문자열이 아니거나, 앞에 대문자 코드가 없거나, 코드 뒤에 단어 경계가 없음) B7 `CAP_SET_UNPARSED`. 이 경우는 LLM 실행 세션이 달라도(timing) B7로 남긴다(느슨하게 B6으로 만들지 않음 — 지시문 "하나라도 있으면 B7").
  3. 뽑은 코드 집합 = 코어 집합이면 B1 `SAME`.
  4. 다르면 변경 전처럼 timing이면 B6 `CAP_SET`, 아니면 B7 `CAP_SET`.
- compare.json의 `llm` 칸에는 원래 문자열 목록(정렬만, 변경 전과 같음)을 그대로 남긴다.

## 테스트 — `manage-us-stock-strategy/tests/test_auto_core_compare_fix.py` (12개)

테스트 파일에는 변경 전 `group_margins` 본문을 `old_group_margins`로 그대로 복사해 두고 "변경 전" 기준으로 쓴다(T3·T5).

| 지시 | 테스트 | 확인 내용 |
|---|---|---|
| T1 | `test_t1_hit_event_group_uses_the_firing_session` | C4− 충족일 = t−2(창 안 유일한 발생 확인), 충족일 여유 0.1% ≤ 1%, 마지막 세션 여유 > 5%. `margins["false_breakout"]` = 충족일 여유, 코어 hit·LLM 없음 → B2. 변경 전 계산(패치)으로는 같은 차이가 B7. 나머지 그룹 값은 변경 전과 같음 |
| (T1 보강) | `test_be_case_2026_10_13_numbers` | BE 실제 수치(295.852 > 291.300, 291.22, 마지막 262.33): 새 여유 0.000275, 옛 여유 0.1278 → B2 `MARGIN:0.0003<=0.01` |
| T2 | `test_t2_wide_event_day_margin_stays_b7` | 같은 모양, 충족일 여유 5% → B7 `UNEXPLAINED` |
| T3 | `test_t3_not_hit_event_groups_and_state_groups_keep_the_last_session` | 충족일이 창 밖(t−5)이라 none인 C4−: margins 전체가 변경 전과 같음. 다른 두 열에서도 hit가 아닌 그룹과 상태형 그룹(trend_recover 등) 값이 변경 전과 같음 |
| T3 보강 | `test_unknown_event_state_keeps_the_last_session` | 봉 불완전으로 C2가 hit가 아닐 때 C2 그룹 값이 변경 전과 같음 |
| (Judge 3) | `test_event_day_is_none_unless_hit` | `_event_day`: 창 안 → 그날, t−5 → None, 반대 쪽 해소 → None, unk → None, 반대 쪽 뒤 재발생 → 마지막 발생일 |
| (카드) | `test_card_alias_of_an_event_rule_uses_its_firing_session` | 위 "카드 별칭 처리" |
| (C7) | `test_research_groups_are_not_moved` | C7 그룹은 대상 아님, 사건형 밖 그룹 이름은 무시 |
| T4 | `test_t4_cap_set_by_ticker` | `["MVLL"]` vs `["MVLL 명목 0.4111 > 0.4"]` → B1(llm 칸 원문 유지), vs `["SOXL 명목 0.5 > 0.4"]` → B7 CAP_SET, vs `["명목 초과"]` → B7 CAP_SET_UNPARSED, `[]` vs `[]` → B1 |
| T4 보강 | `test_partial_parse_and_timing` | 일부만 못 뽑음 → UNPARSED, 종목 추가 → CAP_SET, 소문자·코드 뒤 경계 없음 → B7, 다른 세션 → B6 CAP_SET, 순서만 다름 → B1 |
| T5 | `test_t5_decide_record_unchanged_except_margins` | test_auto_core_decide의 `Env` 픽스처 3가지(기본, `_soxl_two_new_cues`, 충족일이 t−2인 SOXL 열)로 decide를 새 코드와 변경 전 margins(패치)로 각각 돌려, `margins`·`journal` 블록을 뺀 결정 기록 전체(status·reasons·tickets·blocked·candidates·buy_requirements·evidence·no_action·alerts·alert_states·exposure·shock·compare·dashboard·symbols의 groups/triggers/indicators)가 같음. 주문표 decision_key 같음. 일지 payload(`auto_core_payloads`)는 `decision_sha256`을 뺀 나머지가 같음 |
| T5 보강 | `test_t5_margins_differ_only_for_hit_event_groups` | 바뀐 margins 값은 hit인 사건형 그룹 하나(SOXL false_breakout)뿐 |

실행 결과:

- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_compare_fix.py"` → Ran 12, OK
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"` → **Ran 324, OK (skipped=1)**. skip 1개는 기존 `test_auto_core_replay.py`의 `skipUnless`(30분 봉 페이지는 메인 체크아웃에만 있음, worktree에서는 skip) — 이번 변경과 무관, 새 skip 없음.
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → PASS

## 2026-10-13 BE 사례 예상 범주

C4− 충족일 10-07: 돌파선 291.300, 그날 종가 291.22 → 여유 0.08 ÷ 291.22 = 0.000275(0.03%). 오늘(10-12) 코어 상태는 hit(충족일 포함 5세션 안, 반대 쪽 C4+ 발생 없음)이므로 충족일 여유를 쓴다. false_breakout은 EMA 그룹이 아니어서 한계는 1%(종가 차이가 있으면 3%) → **B2 DATA_DEFINITION** (`MARGIN:0.0003<=0.01`). b2_wide 목록에는 들어가지 않는다(1% 이하). 같은 수치를 넣은 테스트 `test_be_case_2026_10_13_numbers`가 이를 확인한다.

MVLL exposure:caps 사례(`["MVLL"]` vs `["MVLL 명목 0.4111 > 0.4"]`)는 **B1 SAME**이 된다.

## 남은 위험

1. **결정 식별 해시(`decision_sha256`, 일지 review_id)**: `auto_core_decide.decision_identity_hash`는 `symbols`(따라서 `margins`)를 포함한 기록 전체의 해시다. 사건형 그룹이 hit이고 충족일이 마지막 세션보다 앞인 날에는 margins 값이 바뀌므로 이 해시 값도 변경 전과 달라진다. 판정·주문표·관문·알림·일지 payload의 다른 칸은 같다(T5). 영향: (a) 지금은 compare 모드라 일지를 쓰지 않음, (b) apply 모드에서 병합 직전·직후에 같은 날 decide를 다시 돌리면 R2-5 재실행 검사가 다른 기록으로 보고 HOLD로 둔다(fail closed, 쓰기 없음). `decision_identity_hash`에서 margins를 빼는 것은 allowed_paths 밖(auto_core_decide.py)이라 하지 않았다. 필요하면 별도 작업.
2. 한 그룹에 사건형 hit 기여자가 둘 이상이면 가장 늦은 충족일을 쓴다. 현재 규칙·카드 구성(카드 별칭이 공통 규칙을 대신함)에서는 생기지 않는다.
3. LLM capBreaches 항목이 소문자 코드이거나 코드 바로 뒤에 한글이 붙어 있으면(`MVLL명목`) UNPARSED → B7로 남는다(의도된 fail-closed). 코드 뒤 공백이나 문장부호가 있으면 정상 인식.
4. 충족일 값은 충족일 당시 봉으로 다시 계산한다(같은 계열 안의 지난 인덱스). 그 사이 분할 조정 등으로 과거 봉이 바뀐 경우에는 조정 후 값이 쓰인다(판정 계산과 같은 계열이라 판정과는 일치).
5. 대조 결과는 표시·완료 증거 전용이다. 이 변경으로 B7 → B2로 바뀌는 항목이 생기면 연속 일수(streak) 계산에 유리해질 수 있다. 부록 B 한계값(B2_PRICE_MARGIN 0.01, B2_HLV_MARGIN 0.03, B2_KNOWN_MARGIN 0.03, B2_N_MARGIN 0.03, B2_R5_MARGIN 0.01)과 범주 이름은 바꾸지 않았고 새 범주도 없다.

## 지켜야 할 것 확인

- 권한 표지 줄(`order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`): 고친 두 스크립트와 새 테스트에 해당 문자열 0건, diff에 없음.
- 키움 호출·주문 경로 없음. 진짜 auto_core.py·run_auto_core.ps1 실행 없음(테스트는 `-p "test_auto_core*.py"` 패턴만).
- 정책·상태 파일, 기존 테스트 파일, CLAUDE.md·AGENTS.md·.claude/·tools/ 변경 없음. 커밋·git add 없음.
