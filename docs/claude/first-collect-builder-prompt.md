---
id: first-collect-builder-prompt
title: 자동 코어 새 종목 30분봉 첫 수집 시작일 — 고정 2026-04-01 → max(2026-04-01, 오늘−150일)
date: 2026-11-11
class: 권한 경로(auto_core*.py) 버그 수정(dev-run class authority — 경로 때문. 의미상 권한·한도·주문 단계·대조 불변식·킬 스위치 불변)
source: docs/claude/first-collect-proposal-2026-11-11.md 1~4절 · 로그 workspace/outputs/auto-core/logs/auto-core-daily-20261110T211501Z.log(BAR_COLLECTION_FAILED:PLTR:1)
authority: order_authority=false · quantity_authority 값 변경 없음 · 주문 경로 없음 · 정책·상태 파일 쓰기 없음 · 키움 호출 없음
approval: 사장 직접 입력 "승인" 2026-11-11 08:33:23 KST(제안서 6절)
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 first-collect -ApproveAuthority — 경로 때문에 붙는 플래그. 다른 dev-run이 돌고 있으면(_lock) 병합하지 않는다)
---

```dev-run
{"task_id": "first-collect", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 60, "builder_timeout_min": 40, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core.py", "manage-us-stock-strategy/tests/test_auto_core.py", "manage-us-stock-strategy/tests/test_auto_core_first_collect.py", "docs/claude/first-collect-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core): first 30m collection for a new symbol starts at most 150 days back (Kiwoom window no longer reaches 2026-04-01; PLTR first collection failed 2026-11-11)"}
```

## 목표

2026-11-11 06:15 KST 자동 코어 daily가 `BAR_COLLECTION_FAILED:PLTR:1`로 멈췄다. PLTR은 11/07 관심 명단에 새로 들어와 이력이 없다. 이력이 없으면 `auto_core.py:352`가 수집 시작일로 `FIRST_COLLECTION_DAY = date(2026, 4, 1)`(57행)을 쓴다. 그런데 키움 30분봉은 PLTR을 2026-05-01부터만 준다. `pages/PLTR/pltr_30m_20260506_p3.json`은 176행이고 첫 봉이 20260501 04:00이다. 그 앞 요청은 빈 응답이라 `collect_30m.ps1`이 exit 1로 끝났다. 10/29까지 처음 받은 다른 종목(BE·SPY·SOXL 등)은 가장 오래된 봉이 모두 20260401 04:00이었다. 키움 자료의 시작일은 달 경계에서 앞으로 옮겨지는 것으로 보인다. 새 종목 첫 수집의 시작일만 고친다.

## 바꿀 것 (`manage-us-stock-strategy/scripts/auto_core.py`)

1. 57행 아래에 상수 `FIRST_COLLECTION_LOOKBACK_DAYS = 150`을 추가한다. 위에 주석 1~2줄(ASCII)을 단다: Kiwoom 30m data starts at a month boundary that moves forward (2026-04-01 for fetches up to 10/29, 2026-05-01 on 11/11), so a fixed first day falls out of it; 150 days keeps >= 31 days of margin.
2. 352행 `oldest = date.fromisoformat(last_session) if last_session else FIRST_COLLECTION_DAY`의 else 쪽을 `max(FIRST_COLLECTION_DAY, today - timedelta(days=FIRST_COLLECTION_LOOKBACK_DAYS))`로 바꾼다.
3. 35행 `from datetime import date, datetime, timezone`에 `timedelta`를 더한다.

그 밖은 바꾸지 않는다. 다음은 그대로 둔다.
- 이력 있는 종목의 시작일(last_session).
- `collect_bars`·`collect_30m.ps1`(빈 응답 = 실패, fail-closed).
- `update_history`·이력 검증·`resolve_exchange`.
- 종목 목록(`symbols_for_run`)·그 밖의 단계·결과 필드.

## 기존 테스트 1줄 (이것만 허용)

`manage-us-stock-strategy/tests/test_auto_core.py:1313` `self.assertEqual(newcomer, ("NEWW", "NASDAQ", "2026-10-14", "2026-04-01"))`는 fixture NOW(KST 2026-10-14, 같은 파일 41행)에서 이력 없는 NEWW의 oldest를 고정값 4/1로 확인한다. 새 규칙에서는 2026-10-14 − 150일 = `"2026-05-17"`이다.
- 그 줄의 기대값 `"2026-04-01"`만 `"2026-05-17"`로 바꾼다.
- 단언을 지우거나 약하게 바꾸지 않는다.
- 같은 줄 바로 위에 주석 1줄(ASCII)을 단다: first collection starts at max(FIRST_COLLECTION_DAY, today - FIRST_COLLECTION_LOOKBACK_DAYS) (first-collect 2026-11-11).
- test_auto_core.py의 다른 줄은 고치지 않는다.
- 이 파일은 작업 트리 CRLF(git i/lf)이니 줄바꿈을 지킨다. 보고에 `git diff --ignore-cr-at-eol --stat`을 적는다.

## 새 테스트 — `manage-us-stock-strategy/tests/test_auto_core_first_collect.py`

선례 `manage-us-stock-strategy/tests/test_auto_core_reconcile_orddt.py:184-231`처럼 만든다. test_auto_core의 `DailyTests`를 상속하고(`base.DailyTests`), `load_tests`로 이 파일의 테스트만 돌게 한다. 상속한 테스트가 두 번 돌지 않게 한다. fixture의 NOW·RECORD(test_auto_core.py:41-42)를 그대로 쓴다. 날짜를 바꾸면 체결 조회 창 14일(auto_core_reconcile.py:83)에 걸려 수집 전에 대조가 FAIL한다. 그러니 다른 날짜로 실행하지 않는다.
1. fixture NOW에서 이력 없는 NEWW의 collector oldest가 `"2026-05-17"`이다.
2. 이력 있는 AAA(last_session 2026-10-12)의 oldest가 `"2026-10-12"`이다(전과 같음).
3. `mock.patch.object(auto_core, "FIRST_COLLECTION_DAY", date(2026, 6, 1))` 아래에서 NEWW의 oldest가 `"2026-06-01"`이다. 고정일이 더 늦으면 고정일을 쓰는지(max) 확인한다.
4. 상수 `auto_core.FIRST_COLLECTION_LOOKBACK_DAYS == 150`, `auto_core.FIRST_COLLECTION_DAY == date(2026, 4, 1)`.

키움·kiwoomcli·PowerShell을 실제로 부르는 테스트는 만들지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)

1. auto_core.py diff는 위 1~3뿐이다(상수·주석, 352행 else 쪽, import 1곳). 기존 테스트 변경은 위 '기존 테스트 1줄'뿐이다.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`가 들어간 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열(`/api/us/ordr`, `ust2000x`, `kiwoom_order`, `order_submit`)을 넣지 않는다.
3. 키움·kiwoomcli·auto_core.py·run_auto_core.ps1·collect_30m.ps1을 실행하지 않는다. 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"`으로만 돌린다. 명령에 auto_core.py 문자열을 넣지 않는다.
4. 고치는 기존 파일의 작업 트리 줄바꿈(CRLF)을 지킨다.

## 보고 `docs/claude/first-collect-report.md`

보고에 넣을 것:
- 바꾼 줄(파일:줄)과 새 테스트 4개.
- 대상 테스트 결과(Ran 수, 실패 0)와 `git diff --ignore-cr-at-eol --stat`.
- 남은 위험: 키움 자료 시작일이 150일 안쪽으로 옮겨지면 그 종목은 여전히 fail-closed로 멈춘다(보이는 실패). 시작일이 옮겨지는 규칙은 확인 필요다.

## Judge 확인 항목

1. diff가 상수·주석, 352행 else 쪽, timedelta import, test_auto_core.py:1313 기대값(+주석), 새 테스트 파일, 보고뿐이다.
2. 새 테스트가 바뀐 동작을 실제로 잡는다. 352행을 되돌리면 테스트 1이 실패한다(oldest가 2026-04-01이 됨). max를 빼면 테스트 3이 실패한다.
3. 이력 있는 종목 경로·collect_30m.ps1·이력 검증·종목 목록이 그대로다.
4. 권한 표지 줄·주문 경로 변경이 없고, 키움 호출과 정책·상태 파일 변경도 없다.
5. 대상 테스트가 전부 통과한다. test_auto_core.py:1313 기대값 변경("2026-04-01" → "2026-05-17" = 2026-10-14 − 150일)은 단언 약화가 아니다.
6. G9: 새 산출(출력 파일·알림·화면 칸·예약)이 없으므로 '해당 없음'이다.
