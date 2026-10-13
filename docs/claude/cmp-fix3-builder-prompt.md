---
id: cmp-fix3-builder-prompt
title: 판정 대조 RG1 분류 — 연구 기록 공백(rg1_coverage)으로 코어가 unk인 RG1 차이를 사전 등록 B4로
date: 2026-10-13
class: 권한 경로(auto_core*.py, tests/test_auto_core*.py) 분류 변경(dev-run class authority — 경로 때문. 대조 결과는 표시·완료 증거 전용, 권한 없음. 판정·주문표·관문·결정 키 불변)
source: docs/claude/redesign-t2-firstrun-report-2026-10-13.md 17절·17-1 재검토 · 사용자 결정 "결정 cmp-fix3: 승인"(2026-10-13 15:01 KST)
authority: order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음 · 판정(state)·주문표·관문 결과 불변
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 cmp-fix3 -ApproveAuthority — 경로 때문에 붙는 플래그)
---

```dev-run
{"task_id": "cmp-fix3", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 80, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_compare.py", "manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py", "docs/claude/cmp-fix3-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core compare): RG1 unknown from a research-record gap (rg1_coverage) is pre-registered B4"}
```

## 목표

비교 모드 대조에서 R-REC1 RG1 차이 하나가 사전 등록 범주(B4 RESEARCH_RECORD, detail `RG1_NEEDS_RESEARCH_RECORD`)에 들어가야 하는데 B7로 떨어진다. 대조 모듈의 **분류 조건만** 고친다. 판정 값·주문표·관문·알림·일지·결정 키는 한 글자도 바뀌지 않는다. auto_core_compare.py 말고 다른 스크립트는 고치지 않는다.

## 결함

- 사전 등록: `auto_core_compare.py`의 RREC 게이트 루프(263행 근처) `elif gate == "RG1" and not research_ok:` → B4 `RG1_NEEDS_RESEARCH_RECORD`, 매수 요건 ⑤(216행 근처) `elif index == 4 and not research_ok:` → 같은 B4.
- 지금 조건은 오늘 연구 기록 상태(`research_ok`)만 본다. 그러나 코어 RG1은 r2 R2-4에 따라 사건 다음 세션부터 평가 세션까지 **모든 세션**에 유효 연구 기록이 있어야 한다(`auto_core_rules.py` R-REC1 docstring 744행 근처, 결과 `shock.rg1_coverage.missing_sessions`). 오늘 기록이 OK여도 지난 세션 기록이 없으면 코어 RG1은 unk다.
- 실제 사례(2026-10-13 14:33 KST decide, 커밋 73e18b4): 결정 기록 최상위 `shock` = event EV3a 2026-10-08, `rg1_coverage` = {from 2026-10-09, to 2026-10-12, missing_sessions [2026-10-09]}(연구 기록은 기록일 2026-10-13 = 세션 10-12부터만 있음), `rg.RG1` = "unk", 통합점검 rg1 = true → B7 UNEXPLAINED. 사전 등록 뜻으로는 B4.

## 바꿀 것 (auto_core_compare.py만)

1. 도움 함수 `_rg1_record_gap(core_shock) -> bool`: `core_shock`(결정 기록 최상위 `shock`)의 `rg1_coverage`가 dict이고 그 `missing_sessions`가 비어 있지 않은 list면 True, 그 밖(None·빈 목록·형식 다름)은 False.
2. RREC 게이트: `gate == "RG1"`이고 `not research_ok` **또는** (`core_value == "unk"` 이고 `_rg1_record_gap(core_shock)`)이면 B4 `RG1_NEEDS_RESEARCH_RECORD`. 코어 RG1이 "no"(훼손 사실)거나 "ok"면 지금과 같다. timing(B6)이 먼저인 순서는 그대로.
3. 매수 요건 ⑤(index 4): 지금 조건에 더해, 그 종목의 `decision["shock"]["by_symbol"][code]["rg"]`가 RG1 "unk"·RG2/RG3/RG4 모두 "ok"이고 `_rg1_record_gap(decision["shock"])`가 True일 때만 B4. 종목 항목이 없거나 다른 게이트가 "ok"가 아니면 지금처럼. ⑤ 칸이 R-REC1 말고 다른 이유로도 막힐 수 있는지 칸을 만드는 코드를 읽어 확인하고, 그렇다면 그 다른 이유가 없을 때로 더 좁힌 뒤 보고서에 적는다.
4. 부록 B 범주 이름·한계값을 바꾸지 않고 새 범주를 만들지 않는다.

## 테스트 — 새 파일 `manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py`

기존 테스트 파일은 고치지 않는다. 기존 `test_auto_core*.py` 전부 통과.

- T1 10/13 사례 합성: research_ok True, 코어 RG1 "unk", rg1_coverage.missing_sessions ["2026-10-09"], 통합점검 rg1 true → RREC:RG1 = B4 `RG1_NEEDS_RESEARCH_RECORD`, unexplained에 없음.
- T2 missing_sessions [] (공백 없음), 코어 unk, 통합점검 true → B7 그대로.
- T3 코어 RG1 "no", 공백 있음 → B7 그대로(훼손 사실로 막힌 것을 B4로 숨기지 않음).
- T4 research_ok False → 지금처럼 B4.
- T5 매수 요건 ⑤: 종목 rg {RG1 unk, RG2 ok, RG3 ok, RG4 ok} + 공백 + 통합점검 ⑤ ok → B4. {RG1 unk, RG2 no, …} + 통합점검 ⑤ ok → 지금처럼 B7.
- T6 timing True → B6 그대로.
- T7 `day_passes`: T1 기록에서 다른 B7이 모두 LLM_ERROR로 설명되면 그 날 통과.

## 지켜야 할 것 (어기면 Judge FAIL)

1. diff는 auto_core_compare.py, 새 테스트 파일, 보고서뿐. auto_core_rules·decide·tickets·reconcile·inputs 무변경.
2. 바뀌는 것은 compare 항목의 category·detail(과 unexplained 목록)뿐. 판정 state·주문표·관문(G0~G5)·매수 요건 칸 값·알림 줄·일지 payload·결정 키 불변.
3. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 들어간 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열 금지.
4. 스크립트 ASCII만(한국어는 `\u` 이스케이프). Claude Code 설정상 "auto_core.py"가 들어간 명령은 거부되므로 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"` 패턴으로만 돌린다. 진짜 auto_core.py·run_auto_core.ps1·키움을 실행하지 않는다.

## 보고 `docs/claude/cmp-fix3-report.md`

바꾼 줄, ⑤ 칸이 막히는 다른 이유를 확인한 방법과 결과, 테스트 결과(Ran 수), 2026-10-13 14:33 기록에 넣었을 때 예상 범주(RREC:RG1 = B4, B7 4건 남음), 남은 위험.

## Judge 확인 항목

1. diff가 auto_core_compare.py·새 테스트·보고서뿐이다.
2. B4 추가 조건이 `core_value == "unk"` 그리고 missing_sessions 비어 있지 않음으로 좁다(T2·T3) — 코어 "no"나 공백 없는 unk는 B7로 남는다.
3. ⑤는 R-REC1 중 RG1만 막는 경우로 한정된다(T5).
4. timing 우선 순서·부록 B 범주·한계값 불변, 새 범주 없음.
5. 판정·주문표·관문·알림·일지·결정 키 불변(compare 모듈 밖 diff 없음).
6. 권한 표지 줄·주문 경로 문자열 변경 없음, 키움 호출 없음, 정책·상태 파일 변경 없음.
7. 기존 테스트 파일 무변경, `test_auto_core*.py` 전부 통과.
