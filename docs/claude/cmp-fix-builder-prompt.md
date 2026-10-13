---
id: cmp-fix-builder-prompt
title: 판정 대조(auto_core_compare) 분류 결함 2건 — 사건형 트리거 여유를 사건일에서 재기, 종목 상한 집합 비교를 종목 코드로
date: 2026-10-13
class: 권한 경로(auto_core*.py, tests/test_auto_core*.py) 표시·분류 변경(dev-run class authority — 경로 때문. 대조 결과는 표시·완료 증거 전용, 권한 없음. 판정·주문표·관문·결정 키 불변)
source: docs/claude/redesign-t2-compare-b7-2026-10-13.md(BE:false_breakout·exposure:caps = CORE_BUG) · 사용자 결정 "결정 t2-equity-cash: 나"(2026-10-13 09:21 KST, 대조 모듈 수정 큐 승인 포함)
authority: order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음 · 판정(state)·주문표·관문 결과 불변
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 cmp-fix -ApproveAuthority — 경로 때문에 붙는 플래그, 사용자 결정 있음)
---

```dev-run
{"task_id": "cmp-fix", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 100, "builder_timeout_min": 60, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_rules.py", "manage-us-stock-strategy/scripts/auto_core_compare.py", "manage-us-stock-strategy/tests/test_auto_core_compare_fix.py", "docs/claude/cmp-fix-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core compare): event-rule B2 margin on the event day; cap set compared by ticker"}
```

## 목표

재설계 T2 비교 모드 1일차(2026-10-13) 차이 8건 중 2건은 트리거 판정이 아니라 **대조 모듈의 분류**가 틀렸다(부록 B 사전 등록 범주는 그대로). 이 두 곳만 고친다. 판정 값(state)·주문표·관문·알림·일지는 한 글자도 바뀌지 않는다.

## 결함 1 — 사건형 트리거의 B2 여유를 마지막 세션에서 잰다

- 부록 B: "B2 DATA_DEFINITION: 코어 값이 그 조건 경계에서 가까움: 가격 조건 여유 ≤ 종가의 1.0% … ① 종가(코어 = 마지막 정규장 봉 종가, LLM = 16:00 봉 시가) … 이 넷에 걸린 조건은 여유 ≤ 3%까지 B2".
- 규칙 파일 113행: 사건형(C2·C4·C6·C7)은 "충족일 포함 5세션 동안 1개로 센다". 즉 사건형이 오늘 hit인 이유는 **충족일**의 조건이다.
- 지금 코드: `auto_core_rules.group_margins(series, c8)`(610행)이 모든 그룹의 여유를 마지막 세션 t에서 잰다. `auto_core_compare._category_for_trigger`가 그 값으로 B2를 판단한다.
- 실제 사례(2026-10-13, BE): C4- 충족일 10-07 — 10-06 종가 295.852 > 돌파선 291.300, 10-07 종가 291.22 < 291.300(여유 0.03%). 오늘(10-12) 여유는 |262.33 − 295.852| ÷ 262.33 = 12.8% → B7로 분류됨. 충족일 여유로 재면 B2.

바꿀 것:
1. 사건형 그룹(false_breakout, false_breakdown, rebound_fail, pullback_rebound, overheat_fade, oversold_rebound — C7 good_news_drop·bad_news_rise는 연구 기록 그룹이라 그대로)에서 **코어 상태가 hit일 때만**, 여유를 그 hit를 만든 충족일(`_event_state`가 쓰는 창 안의 마지막 raw True 세션 = `fired[-1]`)의 값으로 잰다. 그날의 판정 수치는 지금 group_margins와 같은 "결정 수치·선"(예: false_breakout = 그날 종가 vs 그날의 직전 20세션 종가 고점, rebound_fail·pullback_rebound = 그날 종가 vs 그날 EMA20, C2 = 그날 고가·저가 vs 그 전날 EMA20 ± 띠)이고, 나누는 값은 그날 종가다.
2. 코어 상태가 hit가 아니면(none·unk) 지금처럼 마지막 세션 t에서 잰다(바꾸지 않는다). 상태형 그룹(C1·C3·C5)과 rsi_gap·crash/spike도 그대로.
3. 카드 별칭이 사건형 공통 규칙을 대신하는 경우(`CARD_KINDS`, 예: 눌림 반등 U6 = C6+)도 같은 그룹이면 같은 방식. 카드 값 배열(card_raw)을 쓰는 그룹은 그 배열의 충족일을 쓴다. 구현이 복잡해지면 공통 규칙 배열만 처리하고 카드 별칭은 지금처럼 두되 보고서에 적는다.
4. 결과는 지금처럼 `result["margins"][group]` 한 값(float|None). 결정 기록 스키마·키 이름은 바꾸지 않는다. 필요하면 `margins` 계산 위치를 `raw_common` 계산 뒤로 옮긴다.

## 결함 2 — 종목 상한 초과 집합을 문자열 그대로 비교한다

- 실제 사례: 코어 `["MVLL"]`, LLM `account.exposure.capBreaches = ["MVLL 명목 0.4111 > 0.4"]` → 같은 종목인데 B7 CAP_SET. 규칙 파일 155행은 capBreaches[] 형식을 종목 코드로 한정하지 않는다.
- 바꿀 것(`auto_core_compare.py` 213행 근처): LLM 항목마다 앞쪽 종목 코드(`^\s*([A-Z][A-Z0-9.]{0,9})\b`)만 뽑아 집합으로 비교한다. 코드를 못 뽑은 항목이 하나라도 있으면 지금처럼 B7(detail `CAP_SET_UNPARSED`). 같으면 B1 SAME, 다르면 지금처럼 B6(timing)/B7 CAP_SET. compare.json의 `llm` 칸에는 원래 문자열 목록을 그대로 남긴다.

## 테스트 — 새 파일 `manage-us-stock-strategy/tests/test_auto_core_compare_fix.py`

기존 테스트 파일은 고치지 않는다. 기존 `test_auto_core*.py` 전부 통과.

- T1 사건형 충족일 여유: 합성 종가 열(정규장 종가, EMA20·20세션 고점이 계산되는 길이)로 C4- 충족일이 마지막 세션보다 2~3세션 앞이고 충족일 여유 ≤ 1%, 마지막 세션 여유 > 5%인 경우 → `margins["false_breakout"]`이 충족일 여유와 같고, 코어 hit·LLM 없음 차이가 B2로 분류.
- T2 같은 열에서 충족일 여유가 5%면 B7 그대로.
- T3 코어 상태 none인 사건형 그룹은 margins 값이 변경 전과 같다(마지막 세션). 상태형(trend_recover 등) 값도 변경 전과 같다.
- T4 caps: `["MVLL"]` vs `["MVLL 명목 0.4111 > 0.4"]` → B1. `["MVLL"]` vs `["SOXL 명목 0.5 > 0.4"]` → B7 CAP_SET. `["MVLL"]` vs `["명목 초과"]` → B7 CAP_SET_UNPARSED. 빈 목록끼리 → B1.
- T5 불변: 기존 decide 픽스처(test_auto_core_decide·test_auto_core_compare에서 쓰는 것)로 만든 결정 기록에서 `margins`를 뺀 나머지(groups·triggers·state·tickets·blocked·decision keys)가 변경 전과 같다.

## 지켜야 할 것 (어기면 Judge FAIL)

1. 트리거 state·previous_state·new, 주문표, 관문(G0~G5), 매수 요건, 알림 줄, 일지 payload, 결정 키가 변경 전과 같다. 바뀌는 것은 `margins`의 사건형·hit 그룹 값과 compare.json의 category·detail뿐.
2. 부록 B 한계값(B2_PRICE_MARGIN 0.01, B2_HLV_MARGIN 0.03, B2_KNOWN_MARGIN 0.03, B2_N_MARGIN 0.03 등)과 범주 이름을 바꾸지 않는다. 새 범주를 만들지 않는다.
3. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 들어간 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열 금지.
4. 스크립트 ASCII만(한국어는 `\u` 이스케이프). Claude Code 설정상 "auto_core.py"가 들어간 명령은 거부되므로 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"` 패턴으로만 돌린다. 진짜 auto_core.py·run_auto_core.ps1·키움을 실행하지 않는다.

## 보고 `docs/claude/cmp-fix-report.md`

바꾼 함수·줄, 사건형 충족일 계산 방법, 카드 별칭 처리 여부, 테스트 결과(Ran 수), 2026-10-13 BE 사례에 넣었을 때 예상 범주(B2), 남은 위험.

## Judge 확인 항목

1. diff가 auto_core_rules.group_margins(및 호출 위치)와 auto_core_compare의 caps 비교, 새 테스트 파일, 보고서뿐이다.
2. 사건형 그룹은 코어 hit일 때만 충족일 여유를 쓰고, none·unk와 상태형은 마지막 세션 값 그대로다(T3).
3. 충족일은 `_event_state`와 같은 창(EVENT_WINDOW_SESSIONS)·같은 반대 쪽 해소 규칙으로 정해진다(hit가 아니면 충족일을 쓰지 않음).
4. caps는 종목 코드 집합으로 비교하고, 코드를 못 뽑으면 B7로 남는다(느슨하게 B1로 만들지 않음).
5. 판정·주문표·관문·알림·일지·결정 키 불변(T5), 부록 B 한계값·범주 불변.
6. 권한 표지 줄·주문 경로 문자열 변경 없음, 키움 호출 없음, 정책·상태 파일 변경 없음.
7. 기존 테스트 파일 무변경, `test_auto_core*.py` 전부 통과.
