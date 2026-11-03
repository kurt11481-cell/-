---
id: dst-label2-report
title: "dst-label2 Builder 보고 — 종가 검증 인정 시차에 -05:00 추가"
date: 2026-11-03
source: "docs/claude/dst-label2-builder-prompt.md, 측정 docs/claude/dst-label-measure-2026-11-03.md"
class: "authority(K3, H2 — 인정 범위 확대). 병합은 사장 승인 + -ApproveAuthority"
---

## 바뀐 줄
- `manage-us-stock-strategy/scripts/regular_session_close_history.py:61-64` — 주석 3줄을 고침(-04:00은 K3/C13 2026-04-01..09-30, -05:00은 2026-11-02 세션 측정 문서, 다른 시차는 측정 전까지 미확인). 64행 `LABEL_VERIFIED_UTC_OFFSETS = ("-04:00", "-05:00")`. 238~239행 판정과 사유 이름 `BAR_LABEL_TIMEZONE_UNVERIFIED_FOR_UTC_OFFSET`, 달력(ACTIVE) 검사, 페이지 해시·재구성·연속성 검사는 그대로다.
- `manage-us-stock-strategy/references/portfolio-exposure-review.md:72` — "(`-04:00` and `-05:00`, measured 2026-11-02),".
- `manage-us-stock-strategy/tests/test_regular_session_close_history.py`
  - 139~142행 (`test_early_close_uses_the_bar_before_the_early_close`): `assertNotIn("BAR_LABEL_TIMEZONE_UNVERIFIED_FOR_UTC_OFFSET", ...)`, 사유가 정확히 `["SESSION_CALENDAR_NOT_ACTIVE"]`인지 확인, `verified` False 유지(이 테스트의 달력은 ACTIVE가 아님). 주석 고침.
  - 144~163행: 이름을 `test_early_close_is_verified_under_the_measured_winter_offset`로 바꿈. `assertIn("-05:00", rsch.LABEL_VERIFIED_UTC_OFFSETS)`을 넣고, patch 없이 만든 결과가 verified=True·사유 []인지 확인. 예전의 "unmeasured" 단언과 patch는 없앰. 주석 고침.
  - 340~359행 새 테스트 `test_unmeasured_offset_still_leaves_the_winter_close_unverified`: ACTIVE 달력에서 상수를 `("-04:00",)`로 patch하면, 같은 겨울 입력(2026-11-27, -05:00)이 다시 verified=False·사유 `["BAR_LABEL_TIMEZONE_UNVERIFIED_FOR_UTC_OFFSET"]`가 된다. `rsch.unverified_reasons`로도 같은 결과(fail-closed 경로 유지).
- `manage-us-stock-strategy/tests/test_score_spy_history.py`
  - 27행: WINTER_SESSION 주석을 "-05:00 close; e3/e4 patch back to the summer-only set so it stays unverified"로 고침.
  - 142~151행 e3, 153~159행 e4: 본문 전체(히스토리 만들기 → 단언)를 `with mock.patch.object(rsch, "LABEL_VERIFIED_UTC_OFFSETS", ("-04:00",)):` 안에 넣음. 단언 문장은 들여쓰기만 바뀌고 글자는 그대로다. 다른 함수는 바꾸지 않음.
- 줄바꿈: `git diff --ignore-cr-at-eol --stat`과 `git diff --stat` 결과가 같다(4 files changed, 50 insertions(+), 29 deletions(-)). 줄바꿈 바뀜 없음.

## 대상 테스트 결과
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_regular_session_close_history*"` → Ran 21 tests, OK
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_exposure*"` → Ran 154 tests, OK
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_score_spy_history*"` → Ran 10 tests, OK
- 전체 스위트와 기준선 비교는 파이프라인이 한다(Builder는 돌리지 않음).

## 남은 위험
- (a) 이 변경은 인정 범위를 넓힌다(H2). 근거는 측정 문서(docs/claude/dst-label-measure-2026-11-03.md 17~27행)의 세 기준이다: 09:30 봉 거래량 급증, 마감 직전 15:30 봉에 거래량 몰림, 06:15 KST(=16:15 EST) 수집 때 마지막 라벨 160000. 공개 공식 종가와 직접 대조하지는 못했다(같은 문서 29~30행) → **확인 필요**로 남는다.
- (b) 다음 서머타임 시작(2027-03-14) 뒤 -04:00 세션은 지금처럼 인정된다. 인정 목록은 "-04:00", "-05:00" 두 개뿐이라 다른 시차는 계속 미확인이다(새 테스트가 지킴).
- (c) 병합 뒤 첫 06:15 실행(다음 날)에서 2026-11-02 이후 세션이 verified로 바뀌는지 봐야 한다(**확인 필요**). 저장된 이력은 실행 때마다 페이지에서 다시 만들어지므로 따로 고칠 파일은 없다고 본다. 다만 이 세션에서 운영 실행으로 확인하지는 않았다(확인 필요).
- (d) 범위 밖 발견: `manage-us-stock-strategy/scripts/validate_integrated_authority_production.py:108-109`가 대상 세션의 개장·마감 시각을 `09:30:00-04:00`·`16:00:00-04:00`으로 고정해 둔다. 고치지 않았고 위치만 적는다.
- 주문·권한 줄: 표지 없음(바뀐 것 없음). 노출 한도·관문·매도 차단도 바뀐 것 없음. 키움 호출, 상태·정책·일지 쓰기, 커밋 모두 하지 않았다.
- 실행 메모: 이 세션에서 줄바꿈 바이트를 세는 셸 명령은 권한 거부로 실행되지 않았다. 줄바꿈 유지는 위의 두 diff stat 비교로 확인했다.
