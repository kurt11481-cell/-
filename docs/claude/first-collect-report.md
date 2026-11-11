# first-collect Builder 보고 (2026-11-11)

지시문: docs/claude/first-collect-builder-prompt.md · 규칙: tools/dev_pipeline/builder-rules.md

## 바꾼 줄

`manage-us-stock-strategy/scripts/auto_core.py`
- 35행: `from datetime import date, datetime, timedelta, timezone` (`timedelta` 추가)
- 58~59행: 주석 2줄(ASCII) — Kiwoom 30m data starts at a month boundary that moves forward ... 150 days keeps >= 31 days of margin.
- 60행: `FIRST_COLLECTION_LOOKBACK_DAYS = 150` (57행 `FIRST_COLLECTION_DAY = date(2026, 4, 1)`은 그대로)
- 355~356행(옛 352행): 이력 없는 종목의 else 쪽만 `max(FIRST_COLLECTION_DAY, today - timedelta(days=FIRST_COLLECTION_LOOKBACK_DAYS))`로 바꿈. 줄 길이 때문에 괄호로 2줄로 나눔. 이력 있는 종목(`date.fromisoformat(last_session)`)과 다음 줄 `collector(..., oldest=min(oldest, today), ...)`는 그대로.

`manage-us-stock-strategy/tests/test_auto_core.py`
- 1313행: 주석 1줄(ASCII) 추가 — first collection starts at max(FIRST_COLLECTION_DAY, today - FIRST_COLLECTION_LOOKBACK_DAYS) (first-collect 2026-11-11).
- 1314행(옛 1313행): 기대값 `"2026-04-01"` → `"2026-05-17"`(fixture NOW = KST 2026-10-14, 10-14 − 150일 = 05-17). 단언은 그대로 assertEqual.

새 파일 `manage-us-stock-strategy/tests/test_auto_core_first_collect.py` — `base.DailyTests` 상속, `load_tests`로 아래 4개만 실행(상속 테스트 중복 실행 없음), fixture NOW·RECORD 그대로.
1. `test_new_symbol_starts_150_days_back` — NEWW oldest `"2026-05-17"`.
2. `test_symbol_with_history_starts_at_its_last_session` — AAA oldest `"2026-10-12"`(전과 같음).
3. `test_later_fixed_first_day_wins` — `FIRST_COLLECTION_DAY`를 2026-06-01로 patch하면 NEWW oldest `"2026-06-01"`(max 확인).
4. `test_constants` — `FIRST_COLLECTION_LOOKBACK_DAYS == 150`, `FIRST_COLLECTION_DAY == date(2026, 4, 1)`.

바뀐 동작을 잡는지: 옛 else(`FIRST_COLLECTION_DAY`)로 되돌리면 테스트 1의 oldest가 2026-04-01이 되어 실패한다. max를 빼고 `today - 150일`만 쓰면 테스트 3의 oldest가 2026-05-17이 되어 실패한다(코드 논리로 확인, 되돌림 실행은 하지 않음).

키움·kiwoomcli·PowerShell을 부르는 테스트는 없다. 권한 표지 4종 줄과 주문 경로 문자열은 건드리거나 넣지 않았다.

## 테스트

- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_first*"` → Ran 4, OK.
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` → Ran 599, OK (skipped=1, 실패 0). skip 1건은 기존 `test_auto_core_replay.py:186`(저장된 30분 페이지가 본 저장소에만 있어 worktree에서 skip) — 이번 변경과 무관하며 skip을 더하지 않았다.

## git diff --ignore-cr-at-eol --stat

```
 manage-us-stock-strategy/scripts/auto_core.py    | 8 ++++++--
 manage-us-stock-strategy/tests/test_auto_core.py | 3 ++-
 2 files changed, 8 insertions(+), 3 deletions(-)
```

`git diff --stat`(줄바꿈 포함)도 같은 수치 — 기존 두 파일의 CRLF가 지켜졌다. 추적 안 된 새 파일: `manage-us-stock-strategy/tests/test_auto_core_first_collect.py`, 이 보고.

## 남은 위험

- 키움 30분봉 자료 시작일이 오늘−150일보다 안쪽으로 옮겨지면 그 새 종목 첫 수집은 여전히 `collect_30m.ps1` 빈 응답 → `BAR_COLLECTION_FAILED`로 멈춘다(fail-closed, 보이는 실패).
- 키움 자료 시작일이 옮겨지는 규칙(달 경계·보존 기간)은 확인 필요다. 관측은 10/29까지 2026-04-01, 11/11 PLTR 2026-05-01 두 점뿐이다.
- G9: 새 산출(출력 파일·알림·화면 칸·예약) 없음 — 해당 없음.
