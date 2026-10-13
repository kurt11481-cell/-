---
id: cmp-fix3-report
title: cmp-fix3 Builder 보고 — RG1 연구 기록 공백(rg1_coverage)으로 코어가 unk인 RG1 차이를 사전 등록 B4로
date: 2026-10-13
source: docs/claude/cmp-fix3-builder-prompt.md
authority: 없음(대조 분류만). 판정·주문표·관문·알림·일지·결정 키 불변. 키움 호출 없음. 정책·상태 파일 변경 없음.
---

## 1. 바꾼 줄 (manage-us-stock-strategy/scripts/auto_core_compare.py만)

- 새 도움 함수 `_rg1_record_gap(core_shock)`: `rg1_coverage`가 dict이고 `missing_sessions`가 비어 있지 않은 list면 True. None·빈 목록·형식 다름은 False.
- 새 도움 함수 `_rg1_gap_only(decision, code)`: 매수 요건 ⑤용. `decision["shock"]["by_symbol"][code]`가 `open is True`, `status == "unk"`, rg = RG1 "unk"·RG2/RG3/RG4 "ok"이고, `_rg1_record_gap(decision["shock"])`가 True일 때만 True.
- RREC 게이트: `elif gate == "RG1" and not research_ok:` →
  `elif gate == "RG1" and (not research_ok or (core_value == "unk" and _rg1_record_gap(core_shock))):`
  timing(B6) 분기가 여전히 먼저다. 코어 "no"·"ok"는 지금과 같다.
- 매수 요건 ⑤: `elif index == 4 and not research_ok:` →
  `elif index == 4 and (not research_ok or (core_cell["s"] == "unk" and _rg1_gap_only(decision, row["code"]))):`
- 부록 B 범주 이름·한계값, CATEGORIES, 다른 분기는 그대로다. 새 범주는 없다. 권한 표지 줄과 주문 경로 문자열은 건드리지 않았다.
- diff: +27 / −2줄. CRLF와 ASCII를 유지했다(`file`: "ASCII text executable, with CRLF line terminators").

## 2. ⑤ 칸이 막히는 다른 이유 — 확인 방법과 결과

`auto_core_tickets.buy_requirements`(⑤ 칸, 268~276행)와 `auto_core_rules.rrec1`(749~874행), `auto_core_decide.py` 925행(`by_symbol`에는 status·open·rg만 들어감)을 읽었다.

⑤ 칸은 종목 R-REC1 결과 하나로만 정해진다.
- `status == "unk"`이면 "unk", 문구는 `reasons`. reasons는 다음 경우에 생긴다:
  - `BENCHMARK_DATA_MISSING`, `BENCHMARK_SIGMA_UNAVAILABLE`: 일찍 반환되어 rg = {}. → RG2~RG4 "ok" 조건에서 걸러진다.
  - `EVENT_LOW_UNAVAILABLE`: rg = {}, open True. → 같은 조건에서 걸러진다.
  - `EV3B_RECORD_GAP:…`(settle): rg는 다 차 있을 수 있지만 `open`이 None이 된다. → **`open is True` 조건을 더해 좁혔다.** 이 경우는 RG1 말고 "EV3 (b) 사건이 가려졌을 수 있음"이라는 다른 이유이기 때문이다.
  - 사건이 열려 있고 게이트 하나라도 None이면 status "unk"(reasons 없음). RG1만 unk인 경우가 바로 이 경우다.
- `open`이고 status가 "no"이면 "no". RG1 "no"이거나 다른 게이트 "no"인 경우인데, rg 조건에서 걸러진다.
- 열린 사건이 없으면 "ok"이고, 차이가 나도 rg·open 조건 때문에 B4가 되지 않는다.

그래서 ⑤ 조건은 `core_cell["s"] == "unk"`, `open is True`, `status == "unk"`, RG1 "unk"·RG2~RG4 "ok", 포트폴리오 `rg1_coverage` 공백일 때로 좁혔다. 이 조건이 모두 맞으면 ⑤를 막는 것은 RG1 하나뿐이다. `damage`(thesis_damage)는 decide에서 늘 list이므로(853행), 연구 기록이 OK인데 RG1이 unk라면 원인은 기록 공백(`recorded` None)뿐이다.

## 3. 테스트

새 파일 `manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py`(16개, ASCII, skip 없음). 기존 테스트 파일은 바꾸지 않았다.

- 도움 함수: 공백 True, None·빈 목록·형식 다름 False. 실제 `rules.rrec1` 출력(EV3a, 다음 세션 기록 없음)에서 `missing_sessions` = [그 세션], RG1 "unk", 함수 True. 공백을 채우면 [] / RG1 ≠ unk / False.
- T1 10/13 사례: RREC:RG1 = B4 `RG1_NEEDS_RESEARCH_RECORD`이고 unexplained에 없다. RG2~RG4는 B1이다.
- T2 공백 없음(`[]`, None) + 코어 unk → B7.
- T3 코어 "no" + 공백 → B7. 코어 "ok"는 지금과 같다(B1 / B7).
- T4 research_ok False → B4(공백 유무·코어 값과 무관하게 지금처럼).
- T5 ⑤: 실제 `tickets.buy_requirements`로 만든 칸. {RG1 unk, 나머지 ok} + 공백 → B4. RG2 no·RG3 no·RG4 unk·RG2 unk → B7. 좁힌 경우(종목 항목 없음, 공백 없음, coverage None, EV3 (b) 공백 open None, 사건 닫힘, RG1 no, 코어 칸 no) → 모두 B7. research_ok False → B4, timing → B6, 같은 상태 → B1.
- T6 timing → B6.
- T7 `day_passes`: T1 기록에 다른 B7 2건(RREC:RG2, RREC:RG4)을 LLM_ERROR로 설명하면 통과하고 streak는 1. 공백이 없으면 RG1이 남아 통과하지 못한다(streak 0). CORE_BUG가 있으면 통과하지 못한다.

실행 결과:
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_compare_fix3.py"` → Ran 16, OK
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"` → **Ran 352, OK (skipped=1)**. skip 1개는 원래 있던 것이고, 새 파일에는 skip이 없다.
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → PASS

## 4. 2026-10-13 14:33 기록에 넣었을 때 예상 범주

결정 기록 최상위 shock: event EV3a 2026-10-08, `rg1_coverage.missing_sessions` = [2026-10-09], `rg.RG1` = "unk", 통합점검 rg1 = true, research_ok True, timing False.
→ **RREC:RG1 = B4 `RG1_NEEDS_RESEARCH_RECORD`**. 그날 B7은 5건에서 **4건**으로 줄어든다(남는 4건의 설명 상태는 redesign-t2-compare-explained.json 기준이며, 이 작업에서는 확인하지 않았다).
그날 매수 요건 ⑤ 차이는 종목 RG2·RG3도 미충족이면 그대로 B7이다(이번 수정의 대상이 아님).
이 예상은 firstrun 보고 17절의 숫자와 기록 형식으로 추론한 것이다. 이 worktree에는 실제 결정 기록 파일이 없어서 그 파일로 다시 돌려 보지는 않았다. 저장된 10-13 대조 블록은 소급해서 바뀌지 않는다(연속 일수는 각 날 저장된 블록으로 센다).

## 5. 남은 위험

- ⑤는 지시문대로 **포트폴리오(SOXX) 기준** `rg1_coverage`를 본다. `by_symbol`에는 종목별 rg1_coverage가 없다(decide 925행). 종목 사건(EV5, 전력 업종 벤치마크)이 포트폴리오 사건과 다르면 공백 판단이 어긋날 수 있다. 다만 연구 기록이 OK이고 damage가 list일 때 종목 RG1이 unk라면 그 종목의 사건 뒤 기록 공백이 원인이므로, 어긋나는 쪽은 "종목에는 공백이 있는데 포트폴리오에는 없음"(B7로 남음, 보수적)이다. 반대 방향 오분류(공백 없는 종목 unk를 B4로 숨김)는 위 이유로 생기지 않는다.
- 이 수정으로 RG1 차이는 이 사건(EV3a 10-08)이 이어지는 동안 B4로 분류된다. 코어 RG1은 여전히 unk라 매수를 막는다(판정 불변, NO_CHANGE). '켜' 시점에 이것이 유일한 매수 막힘이면 firstrun 보고 17-1대로 다시 본다.
- 분류만 바뀐다. decide 기록의 compare 블록 category·detail·unexplained·categories 수만 달라지고, 판정 state·주문표·관문·⑤ 칸 값·알림·일지 payload·결정 키는 compare 모듈 밖이라 바뀌지 않는다.
- 새 테스트 파일은 LF 줄바꿈이다(새 파일이라 규칙상 CRLF 강제 대상은 아님). 줄바꿈 변환 명령은 이 세션에서 권한 승인을 받을 수 없어 실행하지 못했다.
