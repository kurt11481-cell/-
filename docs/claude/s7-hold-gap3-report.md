---
id: s7-hold-gap3-report
date: 2026-10-30
task: s7-hold-gap3
class: authority (K3, H2 제약 완화) — 병합은 사장 승인 뒤
prompt: docs/claude/s7-hold-gap3-builder-prompt.md
---

# s7-hold-gap3 Builder 보고

## 바뀐 줄
- `manage-us-stock-strategy/scripts/portfolio_exposure.py`
  - 596~637행: 새 내부 함수 `_sold_symbol_gap` (건너뛰기 조건 판정; 결과 dict 키·사유 문자열 추가 없음).
  - 650~651행: `evaluate_review_lines` docstring에 `skipped_sessions` 뜻 확장 한 줄(두 줄) 보탬.
  - 755~757행: 보류 구간 밖 세션의 `closing_equity`가 `None`일 때 `_sold_symbol_gap`이 True면 그 세션을 `result["skipped_sessions"]`에 넣고 `continue`(equity·HWM·선·evaluated_through 갱신 없음). 아니면 758행 이하 기존 `EQUITY_GAP:<세션>:<종목>` 그대로.
  - 1007~1017행: `evaluate_peak_reviews` 마지막 미짝 수집에서 포지션 종료 종목의 completed 기록은 미짝으로 세지 않음.
- `manage-us-stock-strategy/tests/test_portfolio_exposure_gap.py` (새 파일, 13개 테스트).
- 이 보고서.
- 기존 테스트 파일은 한 줄도 바꾸지 않았다. 고친 기존 파일의 줄바꿈은 CRLF 그대로(전체 1739줄 모두 CRLF 확인).

## 건너뛰기 조건 (a) — 모두 만족할 때만, 하나라도 아니면 기존대로 EQUITY_GAP 멈춤
세션 s가 현금 흐름·매도 대기 보류 구간 밖이고 `closing_equity(A, s)`가 종가 누락으로 `None`일 때:
1. A = `snapshot_for(s)` 그 객체이고, s 이하로 날짜가 찍힌 기록 중 A보다 as_of가 늦은 것이 없다(as_of 역전 없음).
2. B = s보다 as_of가 늦고 평가 세션 이하인 기록 중 가장 이른 것(같은 날이면 목록 앞쪽). s 뒤의 기록은 모두 목록에서 A 뒤에 있고 state_revision(정수, bool 아님)이 A보다 크다.
3. A와 B 둘 다 `from_ledger_entry`가 True(확정 상태 기록).
4. A와 B의 보유 종목 집합(`held`)이 다르다.
5. 누락 목록의 모든 항목이 A에서 보유이고 B에서 보유가 아니다(판 종목). `CASH`·`SPLIT_RECONCILIATION_REQUIRED:…`는 보유 종목이 아니므로 언제나 멈춤.
- 지시문 조건 1~3에 1·2의 순서 확인과 A의 확정 여부를 더해 더 좁혔다(지켜야 할 것 4: 확신할 수 없으면 건너뛰지 않음). 종가를 0이나 이전 종가로 메우는 코드는 없다.
- 보류 구간(`sale_pending_holds`·현금 흐름 보류)·재평가(`revalue_held_session`)·`NO_CONFIRMED_SNAPSHOT`·`EVALUATION_SESSION_NOT_IN_CALENDAR`·`required_price_missing`·`CLOSE_UNVERIFIED`·정책 숫자 처리는 무변경.

## 미짝 제외 조건 (b)
peak review 일지 기록이 matched가 아니어도, 다음을 모두 만족하면 `unmatched`에 넣지 않는다.
- 평가 세션의 현재 기록이 있다(`current is not None`).
- payload `review_status`가 `"completed"`이고 symbol이 문자열.
- symbol이 현재 보유 종목에 없다.
- symbol이 평가 세션 이하의 `snapshots` 중 하나에서 보유였다(포지션 종료).
한 번도 보유 기록이 없는 종목, 현재 보유 종목의 짝 없는 기록, 판 종목의 completed 아닌 기록은 그대로 `unmatched` → `JOURNAL_REVIEW_UNMATCHED`.

## 대상 테스트 결과 (PYTHONDONTWRITEBYTECODE=1)
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_exposure*"` → Ran 154 tests, OK (새 파일 13개 포함, 기존 test_portfolio_exposure_fail_closed.py 155행 `EQUITY_GAP:{days[2]}:SOXL` 통과).
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_run_portfolio_exposure_review*"` → Ran 29 tests, OK.
- 전체 스위트·기준선 비교는 파이프라인 몫(실행하지 않음).

새 테스트 사례:
- a: A(d0, MVLL 보유)·B(d8=평가일, MVLL 없음), d1~d8 MVLL 종가 없음 → `EVALUATED`, `skipped_sessions` = d1~d7, 평가일 평가됨.
- 10-29 모양(B가 보유 감소 기록): d1~d7은 건너뜀, d8은 매도 대기 보류 → `HELD`/`LINE_EVALUATION_ON_HOLD`, EQUITY_GAP 없음, `SALE_PROCEEDS_PENDING_CASH_CONFIRMATION` 유지.
- b: B에도 있는 SOXL 종가 누락 → `EQUITY_GAP:d3:MVLL,SOXL`.
- c: A·B 보유 집합 같음(수량만 바뀐 경우 포함) → `EQUITY_GAP:d1:MVLL`.
- d: 판 종목 아닌 TQQQ 누락 → `EQUITY_GAP:d2:MVLL,TQQQ`; A 현금 없음 → `EQUITY_GAP:d0:CASH`.
- e: 건너뛴 세션 뒤 평가일 자기자본 9,000(HWM 10,000×0.90) → L1 이벤트 잡힘.
- 확정 아닌 A(활성화 전 기록) → 멈춤; 목록 순서 역전 → 멈춤; `_sold_symbol_gap` 직접 확인(누락 없음·CASH·평가일 뒤 B·다른 기록 객체·리비전 역전/불리언·B/A 미확정·as_of 역전·다음 기록이 아직 보유·A보다 낮은 리비전의 뒤 기록 → 모두 False).
- f: 판 종목 MVLL completed 기록 → 미짝 아님(트리거 비활성); 한 번도 보유 안 한 NBIS → 미짝; 현재 보유 SOXL 짝 없는 기록 → 미짝; 판 종목의 completed 아닌 기록 → 미짝.

## 남은 위험
- (a) 이 변경은 제약 완화(H2)다. 건너뛴 세션에서는 HWM 새 고점도, 선 이탈도 보지 못한다. 그 사이에 실제 고점이 있었으면 HWM이 낮게 남고(선이 낮아져 덜 예민해짐), 그 사이 선 이탈은 이벤트로 남지 않는다. 다음 평가 세션부터 다시 잡힌다.
- (b) 2026-10-29 실제 입력(rev30 as_of 10/20 → rev31 as_of 10/29, MVLL·NBIS 매도)에서 실제로 풀리는지는 이 Builder가 확인하지 않았다(키움·상태·코어 실행 금지). 병합 뒤 다음 코어 실행에서 확인 필요. 10/31 06:15 KST 이전에는 rev31의 보유 감소 때문에 `SALE_PROCEEDS_PENDING_CASH_CONFIRMATION`으로 HOLD가 유지된다(이 변경과 무관, 다음 정상 대조로 풀림 — 확인 필요).
- (c) 같은 구조(대조 기록이 건너뛴 사이에 보유 종목을 판 경우)의 다른 종목 판매에도 같은 규칙이 자동으로 적용된다. 현재 보유 종목 누락·보유가 같은 두 기록 사이 누락은 계속 멈춘다.
- 판 종목의 completed 고점 검토 기록은 이제 어느 이벤트와도 짝이 맞는지 확인하지 않는다(내용이 틀려도 막지 않음). 같은 종목을 다시 사면 그 종목은 현재 보유가 되어 짝 없는 기록이 다시 미짝으로 잡힌다(재매수 첫날 막힐 수 있음).
- 주문·권한 줄: 표지 없음(변경 없음).

## Judge 참고
- 확인 항목 1: diff는 portfolio_exposure.py·새 테스트 파일·이 보고서뿐, 결과 dict 새 키·새 사유 문자열 없음.
- 확인 항목 3 반례: 현재 보유 종목은 B에 있으므로 조건 5에서 걸러져 판 종목으로 위장 불가. as_of·리비전·목록 순서가 어긋나면 열리지 않음(테스트 `test_records_out_of_order_do_not_open_the_skip`, `test_the_skip_check_itself_refuses_reversed_or_unconfirmed_records`).
