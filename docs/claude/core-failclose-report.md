# core-failclose Builder 보고 (C-1 잔여·C-2)

작성 2026-11-02. 지시문 docs/claude/core-failclose-builder-prompt.md. 커밋·병합 없음(작업 트리에만 남김).

## (a) 바꾼 줄
- manage-us-stock-strategy/scripts/auto_core_rules.py:70-72 — 주석, `EV3_LOOSE_LINE`, `EV3_PARSE_REASON` 추가
- manage-us-stock-strategy/scripts/auto_core_rules.py:740-744 — `ev3_parse_reasons` 추가. `EV3_LINE`(69행)·`ev3_dates`(736~737행 부근, 줄만 밀림) 내용은 그대로
- manage-us-stock-strategy/scripts/auto_core_inputs.py:210 — `core_input_guard`에 `parse_reasons` 인자 추가
- manage-us-stock-strategy/scripts/auto_core_inputs.py:215-216 — 설명문
- manage-us-stock-strategy/scripts/auto_core_inputs.py:222 — reasons 초깃값에 `parse_reasons`를 넣음
- manage-us-stock-strategy/scripts/auto_core_inputs.py:250 — 가드 오류 길에서도 `parse_reasons`를 지킴
- manage-us-stock-strategy/scripts/auto_core_decide.py:10-12 — 모듈 설명문
- manage-us-stock-strategy/scripts/auto_core_decide.py:577 — 가드 호출에 `parse_reasons=rules.ev3_parse_reasons(recovery_text)` 전달
- manage-us-stock-strategy/scripts/auto_core_decide.py:581-593 — 경보를 두 줄로 나눔(아래 "결정" 2)
- manage-us-stock-strategy/scripts/auto_core_tickets.py:1137-1139 — `CURRENT_WEIGHT_MISSING` 차단
- manage-us-stock-strategy/tests/test_auto_core_input_guard.py — `Ev3ParseTests`(200행~), `test_a_broken_ev3_line_leaves_a_sell_that_needs_no_candidate`(478행), 머리 설명문
- manage-us-stock-strategy/tests/test_auto_core_tickets.py — `from unittest import mock`, `CurrentWeightTests`(734행~)

줄바꿈은 고친 파일 6개 모두 CRLF 유지(`file`로 확인). 스키마 감사 PASS.

Builder가 정한 것:
1. 사유는 `core_input_guard` **안에** 넣었다. 다만 판정 자체는 decide가 읽은 그 글(`recovery_text`)로 하고 결과만 넘긴다. R-REC1이 쓰는 글과 검사한 글이 같아야 하고, `auto_core_inputs`가 `auto_core_rules`를 가져오지 않아도 된다. 호출 자리는 coreinput2와 같고 리서치 대기 전이다(시험으로 고정).
2. 경보는 지시문에 없던 추가 수정이다. 기존 경보 줄은 사유를 모두 "입력 문서 미커밋"이라고 적어서, 이 사유가 그대로 들어가면 커밋된 문서를 "미커밋 … EV3"로 잘못 알린다. 그래서 `CORE_INPUT_PARSE`를 따로 내고 "형식 깨짐 … Cowork 문서 확인"이라고 쓴다. 기존 `CORE_INPUT_UNCOMMITTED` 줄의 문구와 시험 기대값은 그대로다. 두 종류가 함께 나오면 줄도 두 개다. 사유는 `decision["reasons"]`와 관문에 들어가지 않는다.

## (b) C-1 느슨한 패턴과 지금 문서의 수
- 패턴: `^\s*-(?=.*이벤트)(?=.*\d{4}-\d{2}-\d{2})(?=.*EV3)` (코드에는 한글을 `\uXXXX`로 적음). 앞 공백을 허용하고, 세 조각의 순서는 보지 않는다.
- 지금 문서 docs/claude/recovery-gate-R-REC1-2026-10-09.md: **느슨 1(71행) · 엄격 1(2026-10-08)**. 새 사유 없음(`test_the_current_document_gives_no_new_reason`이 실제 파일로 확인).
- 순서를 안 보는 쪽을 고른 이유: `- 2026-10-08 이벤트(EV3`처럼 순서가 바뀐 줄도 잡기 위해서다. 대가로, 앞으로 45행 같은 메모 줄(날짜+EV3)에 "이벤트"라는 낱말이 들어가면 잘못 막힐 수 있다. 그때는 매수만 막히고 경보가 간다(fail-closed).

남은 한계(지시문대로 둠, 지금 문서에는 해당 없음):
- 같은 날짜의 EV3 줄이 두 개면 느슨 2 > 엄격 1이라 막힌다(줄 수 대 날짜 수 비교, fail-closed 쪽).
- 엄격 패턴은 `(EV`까지만 보므로 `(EV1` 같은 엄격 줄이 있으면 엄격 수가 늘어, 깨진 EV3 줄 하나를 가릴 수 있다.
- 날짜가 YYYY-MM-DD가 아니면(`2026.10.08`) 느슨한 수에도 안 잡힌다.

## (c) C-2 차단 자리와 재배치 후보 영향
- 자리: `_buy_ticket` auto_core_tickets.py:1137. 기존 차단 사유(1129~1131행)와 기준가 검사 뒤, `current` 계산 바로 앞. 기존 사유가 있으면 그 사유가 먼저 나온다(`test_the_block_comes_only_after_the_other_buy_reasons`).
- 재배치 후보: **달라지지 않는다.** 순위는 decide 1133행 `redeploy_ranking`(buy_rows·checks·evidence·scenarios)에서 정해지고, 고르는 일은 plan() 735~742행으로 매수 계획보다 앞선다. 이 차단은 그 뒤 `_buy_ticket`에서 일어나고 후보 계산은 weights를 읽지 않는다.
- 따라서 비중이 빠진 보유 종목도 다른 요건을 채우면 후보로 남는다. 매도 후회표의 후보 칸은 up/down만 쓰므로 영향이 없다. 표시 전용 `swap_pair`의 교체 수만 `trial.get(candidate, 0)`(tickets 1301행)으로 0에서 시작한다. 이 동작은 이번 변경 전과 같고 범위 밖이라 고치지 않았다.
- hold_range는 같은 `_buy_ticket`을 다시 부르지만, 기준 close에서 차단되면 표 자체가 없어 호출되지 않는다.

## (d) 대상 시험
명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`

```
Ran 594 tests in 178.175s

FAILED (failures=1, skipped=1)
```

실패 1건: `test_real_registry_is_schema_valid_and_every_hash_matches`(test_auto_core_decide.py:1339), subTest symbol=PLTR, 사유 `CARD_SECTION_CHANGED`·`CARD_NOT_ACCEPTED_IN_WATCHLIST`.
- 이 시험은 실제 등록부·카드 문서·관심 명단과 `load_registry`·`load_watchlist`·`card_check`·`section_sha256`만 쓴다. 이번 diff는 그 어느 것도 건드리지 않았다.
- 기존 실패로 판단하지만, 지시문의 git 제한 때문에 깨끗한 트리에서 실측하지는 않았다. 새 실패 여부는 파이프라인 기준선 비교로 확정한다. 원인도 **확인하지 못했다**(범위 밖, 데이터 파일 수정 금지).
- 이번 시험이 추가한 14개는 모두 통과했고, 기존 단언·기대값·skip 변경은 없다.

추가 시험 — 지시문 6개 대응:
1. 지금 문서 → 새 사유 없음: `Ev3ParseTests.test_the_current_document_gives_no_new_reason`
2. 띄어쓰기 변형 → 사유·매수 막힘: `Ev3ParseTests.test_a_spacing_variant_of_the_line_blocks_the_buy`
3. EV3 줄 없음 → 새 사유 없음: `Ev3ParseTests.test_a_document_without_an_ev3_line_gives_no_new_reason`
4. 보유 + 비중 없음: `CurrentWeightTests.test_held_without_a_weight_is_blocked`
5. 보유 + 비중 있음 → 같은 수량: `CurrentWeightTests.test_held_with_a_weight_keeps_its_quantity`
6. 첫 매수 + 비중 없음: `CurrentWeightTests.test_first_buy_without_a_weight_starts_from_zero`

그 밖의 추가: `test_a_broken_line_next_to_a_readable_one_is_counted`, `test_lines_that_are_not_event_list_lines_do_not_count`, `test_the_check_runs_before_the_research_wait`, `test_the_reason_survives_a_guard_error_and_stays_out_of_the_decision_reasons`, `test_the_alert_says_the_format_broke_and_not_uncommitted`, `test_both_kinds_of_reason_get_their_own_alert_line`, `test_a_broken_ev3_line_leaves_a_sell_that_needs_no_candidate`, `test_the_block_comes_only_after_the_other_buy_reasons`.

## (e) 그날 매도표 영향
- C-1: 매도 관문·card_check·`_plan_sell`은 그대로지만, 사유가 나온 날은 재배치 후보가 빠져 coreinput2와 똑같이 매도 후회 칸·단계·수량·swap_pair가 달라지거나 그날 매도표가 없을 수 있다(후보 없는 날과 같은 계산).
- C-2: 없음. 후보 선택이 차단보다 앞서고, `plan_premise`는 매도 쪽 차단만 읽으며, `_limit_daily`는 매도를 먼저 남긴다.

표지 없음.

## 범위 밖으로 남긴 것
- manage-us-stock-strategy/references/auto-core-decision.md에는 새 사유·경보 코드를 적지 않았다(허용 파일 밖).
- `auto_core_replay.py`는 `input_block` 없이 돌기 때문에 이번 사유를 보지 않는다(재생 결과 불변).
