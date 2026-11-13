---
id: qqq-b-core-builder-prompt
title: 자동 코어가 QQQ를 '판 몫 보관 지수 ETF'로 알게 하기 (QQQ 등록 단계 B 코드 몫)
date: 2026-11-12
class: 권한 경로(auto_core*.py) — dev-run class authority. 경로 때문에 authority다. 문턱·S7·주문 단계·대조 불변식·킬 스위치·승인 상품 목록(APPROVED_BUY)은 그대로 둔다.
source: docs/claude/qqq-reg-b-proposal-2026-11-12.md 4절 · 사장 결정 t3-proceeds-qqq-1108(docs/claude/t3-proceeds-qqq-2026-11-08.md 0·4절)
authority: order_authority=false · quantity_authority 값 변경 없음 · 주문 경로 없음 · 정책·상태 파일 쓰기 없음 · 키움 호출 없음
approval: 사장 결정 카드 "착수 — 코드부터" 2026-11-13 14:13:55 KST(cmsg_0137MRzn9nuDvvQmVxm6WeX93iiKsXawoSDw7hVfuU64oQ, 누른 계정 = 사장) — 제안서 qqq-reg-b-proposal-2026-11-12.md 11절
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 qqq-b-core -ApproveAuthority. 다른 dev-run이 돌고 있으면(_lock) 병합하지 않는다)
---

```dev-run
{"task_id": "qqq-b-core", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 60, "builder_timeout_min": 40, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_tickets.py", "manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/tests/test_auto_core_qqq_b.py", "docs/claude/qqq-b-core-report.md"], "target_tests": ["test_auto_core*.py", "test_qqq_registration.py"], "commit_message": "feat(auto-core): QQQ as a proceeds-parking index ETF (index-ETF list, no no-card alert; not a card-buy product) — qqq-reg stage B, decision t3-proceeds-qqq-1108"}
```

## 목표

2026-11-08 사장 결정 t3-proceeds-qqq-1108의 내용은 다음과 같다.
- SOXL을 판 돈은 관문이 닫힌 뒤 QQQ에 담아 둔다.
- 카드 매수가 나오면 QQQ를 팔아 재원으로 쓴다.
- QQQ에는 카드가 없다.

QQQ를 사는 길은 통합 점검 규칙 v3.12.15의 '판 몫 줄' 하나뿐이다. QQQ는 카드 매수 길(매수 요건 표·알림 ④·⑨ + 쪽·기록 채점 매수 단위)에 들어가지 않는다.

지금 코어는 QQQ를 들면 다음과 같이 보고, 규칙 v3.12.15와 다르게 나온다.
- 지수 ETF로 보지 않는다. 그래서 ① 칸이 `EARNINGS_DATE_UNVERIFIED` 막힘이 되고, single_nominal에 QQQ가 들어간다.
- 알림 ⑩ "카드 없음 QQQ"를 만든다.

## 바꿀 것

1. `manage-us-stock-strategy/scripts/auto_core_tickets.py` 62행 `INDEX_ETFS` 끝에 `"QQQ"`를 더한다. 결과는 `("SOXL", "TQQQ", "DRAM", "QQQ")`이다.
2. 같은 파일 62행 바로 아래에 다음을 둔다.
   - 상수: `PARKING_ETFS = ("QQQ",)`
   - 그 위 주석 1줄(ASCII): `# Proceeds-parking index ETFs: bought only through the integrated check's proceeds line, never a card buy and never a no-card alert (decision t3-proceeds-qqq-1108).`
3. `APPROVED_BUY`(61행)는 **바꾸지 않는다**. 카드 매수 승인 목록이라 QQQ를 넣으면 다음 셋이 QQQ에 켜진다. 사장 결정과 맞지 않는다.
   - 코어 알림 ④·⑨ + 쪽(auto_core_decide.py:311·346 부근 `buy_approved`)
   - 기록 채점 매수 단위(score_decision_journal.py:1450 부근)
   - replay 열림 판정(auto_core_replay.py:155)
4. `manage-us-stock-strategy/scripts/auto_core_decide.py`의 `alert_candidates`에서 `if result.get("nocard"):`(314행, 파일에 하나) 조건에 `and symbol not in tickets_module.PARKING_ETFS`를 더한다. QQQ에는 ⑩ 줄과 `10:QQQ` state를 만들지 않는다. 같은 파일에서 다른 곳은 고치지 않는다. 트리거 목록의 NOCARD 항목(auto_core_rules.py)은 그대로 두어 비교(compare) 단위가 규칙 기록과 같게 한다.

그 밖은 바꾸지 않는다. 다음은 그대로 둔다.
- `buy_requirements`의 현금 판정과 상품 승인 판정. QQQ(추가) 행의 ②는 "상품 승인 없음" 막힘으로 남는다. 규칙 v3.12.15도 같은 칸에 "막힘 — 판 몫 보관 상품"으로 적는다.
- `rule_file_nominal` 식, `POLICY_EXPECTED`, 재배치 후보, S7, 정책 파일.

## 새 테스트 — `manage-us-stock-strategy/tests/test_auto_core_qqq_b.py`

키움·kiwoomcli·PowerShell을 부르지 않는다. 함수를 직접 부르는 단위 테스트로 만든다. 인자 꾸미는 법은 기존 테스트를 따른다.
- `rule_file_nominal`·`buy_requirements`: tests/test_auto_core_t2rc_corefix.py·tests/test_auto_core_rg1_damage.py
- `alert_candidates`: tests/test_auto_core_rg1_damage.py:362·tests/test_auto_core_risk1r.py:274

1. `INDEX_ETFS == ("SOXL", "TQQQ", "DRAM", "QQQ")`, `PARKING_ETFS == ("QQQ",)`이다. `APPROVED_BUY`는 옛 10개 그대로이고 `"QQQ"`가 없다.
2. `rule_file_nominal`에 BE와 QQQ 보유, multipliers `{"BE": 1, "QQQ": 1}`을 넣는다. `status == "OK"`이고 `single_nominal`에 BE는 있고 QQQ는 없다.
3. `buy_requirements(symbol="QQQ", held=True, …, research_block=None)`의 결과:
   - 첫 칸은 `{"s": "ok", "t": "통과 (지수 ETF — 해당 없음)"}`이다.
   - 둘째 칸은 `s == "no"`이고 글에 "상품 승인 없음"이 있다(카드 매수 길 아님).
4. 같은 호출에 `research_block="X"`를 넣으면 첫 칸 `s == "no"`이다.
5. `alert_candidates`에 보유 QQQ(`nocard: True`)와 보유 BE(`nocard: True`)를 넣는다. 결과 states에 `10:BE`는 있고 `10:QQQ`는 없다.

## 지켜야 할 것 (어기면 Judge FAIL)

1. diff는 위 1·2·4(+주석), 새 테스트 파일, 보고뿐이다. `APPROVED_BUY`는 바이트 그대로다. 기존 테스트 파일은 고치지 않는다.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`가 들어간 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열(`/api/us/ordr`, `ust2000x`, `kiwoom_order`, `order_submit`)을 넣지 않는다.
3. 키움·kiwoomcli·auto_core.py·run_auto_core.ps1을 실행하지 않는다. 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"`으로만 돌린다.
4. 고치는 파일의 작업 트리 줄바꿈을 지킨다. `git ls-files --eol`로 확인하고, auto_core_tickets.py는 w/crlf다. 보고에 `git diff --ignore-cr-at-eol --stat`을 적는다.

## 보고 `docs/claude/qqq-b-core-report.md`

- 바꾼 줄(파일:줄, 앞뒤 값)과 새 테스트 5개.
- 대상 테스트 결과: 패턴별 Ran 수, 실패 0.
- `git diff --ignore-cr-at-eol --stat`.
- `INDEX_ETFS`·`APPROVED_BUY`·`PARKING_ETFS`·`nocard`를 읽는 곳 전부(grep, scripts 전체). 각 곳에서 QQQ 보유 때 바뀌는 동작을 한 줄씩 적는다.
- 남은 위험:
  - 코어 ② 현금은 현금만 센다. 카드 매수 날 현금이 QQQ에 있으면 그날 코어는 "현금 < 1주"이고, QQQ를 판 다음 날 매수를 다시 계산한다.
  - S7은 QQQ에 종목 상한 0.4를 건다(single_stock_cap_exempt 밖).

## Judge 확인 항목

1. diff가 INDEX_ETFS·PARKING_ETFS(+주석), alert_candidates의 nocard 조건 1곳, 새 테스트 파일, 보고뿐이다. APPROVED_BUY는 그대로다.
2. 새 테스트가 바뀐 동작을 실제로 잡는다.
   - INDEX_ETFS에서 QQQ를 빼면 테스트 1·2·3이 실패한다.
   - nocard 조건을 되돌리면 테스트 5가 실패한다.
   - APPROVED_BUY에 QQQ를 넣으면 테스트 1·3이 실패한다.
3. `buy_requirements`·`rule_file_nominal`·재배치 후보·S7·정책 파일·트리거 목록의 NOCARD 항목이 그대로다.
4. 권한 표지 줄·주문 경로 변경이 없고, 키움 호출과 정책·상태 파일 변경도 없다.
5. 대상 테스트가 전부 통과한다.
6. G9: 새 산출(출력 파일·알림 종류·화면 칸·예약)이 없으므로 '해당 없음'이다. QQQ(추가) 행의 ① 칸 값이 바뀌고 QQQ의 ⑩ 줄이 빠질 뿐이며, 둘 다 QQQ를 들 때만 생긴다.
