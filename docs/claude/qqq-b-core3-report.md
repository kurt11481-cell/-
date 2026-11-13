---
id: qqq-b-core3-report
title: qqq-b-core3 Builder 보고 — 자동 코어가 QQQ를 '판 몫 보관 지수 ETF'로 알게 하기 (QQQ 등록 단계 B 코드 몫)
date: 2026-11-13
source: docs/claude/qqq-b-core3-builder-prompt.md · 사장 결정 t3-proceeds-qqq-1108
---

# qqq-b-core3 Builder 보고

## 1. 바꾼 줄

| 파일:줄 | 앞 | 뒤 |
|---|---|---|
| manage-us-stock-strategy/scripts/auto_core_tickets.py:62 | `INDEX_ETFS = ("SOXL", "TQQQ", "DRAM")` | `INDEX_ETFS = ("SOXL", "TQQQ", "DRAM", "QQQ")` |
| manage-us-stock-strategy/scripts/auto_core_tickets.py:63 (새 줄) | — | `# Proceeds-parking index ETFs: bought only through the integrated check's proceeds line, never a card buy and never a no-card alert (decision t3-proceeds-qqq-1108).` |
| manage-us-stock-strategy/scripts/auto_core_tickets.py:64 (새 줄) | — | `PARKING_ETFS = ("QQQ",)` |
| manage-us-stock-strategy/scripts/auto_core_decide.py:305 | `if trigger["side"] == "alert" and trigger["state"] == "review":` | `... and trigger["state"] == "review" and not (trigger["id"] == "NOCARD" and symbol in tickets_module.PARKING_ETFS):` |
| manage-us-stock-strategy/scripts/auto_core_decide.py:314 | `if result.get("nocard"):` | `if result.get("nocard") and symbol not in tickets_module.PARKING_ETFS:` |

`APPROVED_BUY`(auto_core_tickets.py:61)는 바이트 그대로다(diff hunk가 61행에 없음: `git diff -U0` hunk = decide 305·314, tickets 62→62-64).
기존 테스트 파일은 고치지 않았다. auto_core_rules.py(NOCARD 트리거 636-639 포함)·buy_requirements·rule_file_nominal·재배치 후보·S7·정책 파일은 그대로다.

줄바꿈: `git ls-files --eol` → 두 파일 모두 `i/lf w/crlf`(고친 뒤에도 mixed 아님).

## 2. 새 테스트 — manage-us-stock-strategy/tests/test_auto_core_qqq_b.py (5개)

1. `test_1_lists`: `INDEX_ETFS == ("SOXL","TQQQ","DRAM","QQQ")`, `PARKING_ETFS == ("QQQ",)`, `APPROVED_BUY`가 옛 10개 그대로이고 QQQ 없음.
2. `test_2_qqq_not_in_single_nominal`: BE 10주·QQQ 5주, multipliers `{"BE":1,"QQQ":1}` → `status == "OK"`, single_nominal에 BE 있음·QQQ 없음.
3. `test_3_index_etf_cell_and_no_product_approval`: `buy_requirements(symbol="QQQ", held=True, research_block=None, 현금 충분)` → 첫 칸 `{"s":"ok","t":"통과 (지수 ETF — 해당 없음)"}`, 둘째 칸 `s == "no"`이고 글에 "상품 승인 없음".
4. `test_4_research_block_still_blocks`: 같은 호출에 `research_block="X"` → 첫 칸 `s == "no"`.
5. `test_5_no_nocard_lines_for_qqq`: 보유 QQQ·BE, 둘 다 `nocard: True`·auto_core_rules.py:636-639와 같은 NOCARD 트리거, QQQ에는 NOCARD 아닌 ② 트리거 C8-를 더함 → states에 `10:BE`·`2:BE:NOCARD` 있음, `10:QQQ`·`2:QQQ:NOCARD` 없음, `2:QQQ:C8-` 있음(줄도 나옴), "QQQ"와 "카드 없음"을 함께 가진 줄 없음.

테스트가 잡는 변경(코드 읽기로 확인, 뒤집어 돌리지는 않음):
- INDEX_ETFS에서 QQQ 제거 → 1(목록 비교), 2(single_nominal에 QQQ 들어감, tickets.py:186-187), 3(첫 칸이 earnings_blackout 결과로 바뀜, tickets.py:234-237) 실패.
- 314행 조건 되돌림 → 5의 `10:QQQ` 없음 단언과 '카드 없음 QQQ' 줄 단언 실패.
- 305행 조건 되돌림 → 5의 `2:QQQ:NOCARD` 없음 단언 실패.
- 305행 조건이 QQQ의 다른 ② 트리거까지 막음 → 5의 `2:QQQ:C8-` 단언 실패.
- APPROVED_BUY에 QQQ 넣음 → 1(목록 비교)과 3("상품 승인 없음" 사라짐, tickets.py:264-265) 실패.

## 3. 대상 테스트 결과

| 패턴 | Ran | 결과 |
|---|---|---|
| `test_auto_core_qqq_b.py` | 5 | OK |
| `test_auto_core*.py` | 604 | OK (skipped=1, 기존 skip — 이번에 더한 skip 없음) |
| `test_qqq_registration.py` | 8 | OK |

실패 0.

## 4. `git diff --ignore-cr-at-eol --stat`

```
 manage-us-stock-strategy/scripts/auto_core_decide.py  | 4 ++--
 manage-us-stock-strategy/scripts/auto_core_tickets.py | 4 +++-
 2 files changed, 5 insertions(+), 3 deletions(-)
```
(새 파일 2개 — tests/test_auto_core_qqq_b.py, 이 보고 — 는 추적 전이라 stat에 없음.)

## 5. INDEX_ETFS·APPROVED_BUY·PARKING_ETFS·nocard·NOCARD를 읽는 곳 (grep, manage-us-stock-strategy/scripts 전체)

| 곳 | QQQ 보유 때 바뀌는 동작 |
|---|---|
| auto_core_tickets.py:61 `APPROVED_BUY` 정의 | 바뀜 없음(QQQ 없음). |
| auto_core_tickets.py:62 `INDEX_ETFS` 정의 | QQQ가 지수 ETF가 됨. |
| auto_core_tickets.py:64 `PARKING_ETFS` 정의 | 새 상수, decide 305·314만 읽음. |
| auto_core_tickets.py:187 rule_file_nominal single_nominal | QQQ가 single_nominal에서 빠짐(N 합계 n·total은 그대로). |
| auto_core_tickets.py:230·232 buy_requirements ① | QQQ(추가) 행 ①이 `EARNINGS_DATE_UNVERIFIED` 막힘 대신 "통과 (지수 ETF — 해당 없음)"(연구 기록 OK일 때), 연구 기록 not OK면 막힘. |
| auto_core_tickets.py:264 buy_requirements ② 상품 승인 | 바뀜 없음: QQQ ②는 "상품 승인 없음" 막힘 그대로. |
| auto_core_decide.py:305 alert_candidates ② | QQQ의 NOCARD 트리거에서 `2:QQQ:NOCARD` state와 "검토 개시" 줄이 안 생김. QQQ의 다른 ② 트리거·다른 종목 NOCARD는 그대로. |
| auto_core_decide.py:314 alert_candidates ⑩ | QQQ의 `10:QQQ` state와 "카드 없음 QQQ" 줄이 안 생김. 다른 종목은 그대로. |
| auto_core_decide.py:1037 evaluate_symbol `buy_approved` | 바뀜 없음: QQQ buy_approved False → 알림 ⑨ + 쪽(311)·④(346) 꺼진 채. |
| auto_core_decide.py:1248 `_symbol_view` (nocard 키 복사) | 바뀜 없음: decision symbols의 QQQ `nocard: true`는 그대로 남음. |
| auto_core_rules.py:538 `nocard` 계산 | 바뀜 없음(보유·등록부 항목 없음 → True). |
| auto_core_rules.py:636-637 NOCARD 트리거 추가 | 바뀜 없음: decision triggers에 QQQ NOCARD 그대로(비교 단위 유지). |
| auto_core_inputs.py:170 card_check 사유 "NOCARD" | 바뀜 없음(QQQ 카드 사유 NOCARD, 주문표 자격 없음 그대로). |
| auto_core_compare.py:55 `SEPARATE_IDS`의 "NOCARD" | 바뀜 없음: triggers의 NOCARD는 여전히 별도 단위로 비교. |
| auto_core_replay.py:155 replay 열림 `APPROVED_BUY` | 바뀜 없음: QQQ는 replay 매수 열림 대상 아님. |
| auto_core_replay.py:157 replay `INDEX_ETFS` 실적일 | QQQ가 155행에서 먼저 걸러지므로 실제 동작 바뀜 없음. |

(score_decision_journal.py의 매수 단위 판정은 위 이름을 직접 읽지 않아 grep에 안 나온다. 지시문이 든 :1450 부근은 고치지 않았다.)

## 6. 남은 위험

- 코어 ② 현금은 현금만 센다. 카드 매수 날 현금이 QQQ에 있으면 그날 코어는 "현금 < 1주"이고, QQQ를 판 다음 날 매수를 다시 계산한다.
- S7은 QQQ에 종목 상한 0.4를 건다(single_stock_cap_exempt 밖).
- QQQ가 single_nominal에서 빠지므로 코어 매수 요건 ②의 '종목 상한' 사유는 QQQ를 세지 않는다. 종목 상한은 S7 cap_breaches가 계속 잡는다.
- decision의 triggers에는 QQQ NOCARD가 그대로 남는다(compare 단위 유지). 알림 줄만 빠진다.

## 7. 지킨 것

- 키움·kiwoomcli·PowerShell 실행 스크립트·코어 실행기를 돌리지 않았다. 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"`으로만 돌렸다.
- 권한 표지 줄과 주문 경로 문자열을 만들거나 바꾸지 않았다. 정책·상태 파일 변경 없음. 커밋·git add 없음.
- G9: 새 산출(출력 파일·알림 종류·화면 칸·예약) 없음 — 해당 없음.
