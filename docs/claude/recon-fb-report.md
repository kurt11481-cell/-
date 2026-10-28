---
id: recon-fb-report
title: "recon-fb Builder 보고 — B2-N 직전 거래일 행 대체(recon-fallback)"
date: 2026-10-28
class: "authority(K3, H2 증거 요건 완화) — 병합은 사장 승인 + -ApproveAuthority"
source: "지시문 docs/claude/recon-fb-builder-prompt.md, 규칙 tools/dev_pipeline/builder-rules.md"
---

## 바뀐 줄
- `manage-us-stock-strategy/scripts/auto_core_reconcile.py`
  - 778~787행 새 함수 `ledger_read_without_usd_row(results, day)`: 그날 ust21132 읽기가 정확히 1건이고 통과(PASS·페이지 완료)했으며 USD 행이 0개일 때만 True. 읽기 실패·없음·중복, USD 행 1개 이상이면 False.
  - 790~793행 새 함수 `previous_session(calendar, day)`: 운영 달력 `sessions`에서 day보다 앞선 가장 늦은 세션 날짜(없으면 None).
  - 810~816행 `unverified_outflow` docstring에 fallback 조건 추가.
  - 825~830행 `unverified_outflow`: 기존 SPAN_MISMATCH 검사 뒤, 아래 4조건이 모두 맞을 때만 `after = fallback`. 그 뒤 계산(L, 0.05 일치, 한도, 원화 증가 금지, basis)은 기존 줄 그대로이며 바뀐 `after`를 쓴다.
  - 1200~1229행 `run_auto` 안 `outflow_ledger`: 달력을 한 번 읽어 `ledger_days`와 `previous_session`에 같이 쓴다. `ledger_reads` 캐시는 days 키에 ledger 전체(dict)를 담는다(fallback 키는 세 번째 읽기를 했을 때만 있음).
- `manage-us-stock-strategy/references/broker-snapshot-reconciliation.md` 317~333행: B2-N 항목 끝에 "Previous-trading-day fallback" 단락 추가(코드와 같은 조건).
- `manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py` 484행~ 새 클래스 `FallbackLedgerTests`(단위 9개), 566행~ `FallbackRunTests`(실행 1개). 기존 테스트 함수는 한 줄도 바꾸지 않았다.
- 바꾸지 않은 것: `ledger_days`, `ledger_balance`, `cash_flow_evidence.py`, I1·I2·I4·I5, CASH_TOLERANCE_USD, OUTFLOW_MATCH_USD, FILL_WINDOW_MAXIMUM_DAYS, 정산 규칙, 한도 식, 유출만 인정, HWM. `unverified_outflow_basis` 키는 그대로(새 키·새 경고 문자열 없음). 주문·권한 줄은 바꾸지 않았다(표지 없음).

## fallback 조건 4가지 (`unverified_outflow` 825~830행)
1. 읽기 성공·USD 0행: `ledger_read_without_usd_row(results, base_after)`가 True. 읽기 실패(사유 `...:<base_after>`), USD 2행·값 해석 불가(`...:USD_ROW`·`...:VALUE`)는 지금처럼 보류.
2. fallback 날짜 범위: `fallback`이 date이고 `base_before < fallback < base_after`.
3. 창 세션 ≤ fallback: 계산 창의 모든 `session_date`가 `base_before < session_date <= fallback`.
4. fallback 행 정상: `ledger_balance(results, fallback)`가 사유 없음(읽기 1건 통과, USD 행 정확히 1개, fx_entr·won_entr 해석 가능).
하나라도 어긋나면 `after`는 그대로이고, 기존 루프가 `UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:<base_after>:USD_ROW`(또는 기존 사유)로 보류한다.

## 읽기 횟수
- 평소(base_after 행 있음, 읽기 실패, USD 2행 등): 2번. 지금과 같다.
- fallback 때만 3번: base_after 읽기가 통과·USD 0행이고, `previous_session(달력, base_after) > base_before`일 때 그 날짜 한 번 더 읽는다. 앞 세션이 base_before와 같으면(연속 거래일) 읽지 않는다.
- 세 번째 읽기에서 예외가 나면 기존 처리와 같이 `UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:READ_FAILED`(보류). 이 경우는 캐시하지 않으므로 compare 점검이 다시 읽는다(기존 예외 때와 같은 동작).

## 테스트 결과 (PYTHONDONTWRITEBYTECODE=1)
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`: 543개 실행, 실패 1, skip 1.
  - 실패 1건: `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches`(symbol PLTR, `CARD_SECTION_CHANGED`, `CARD_NOT_ACCEPTED_IN_WATCHLIST`). 실제 카드 등록부 자료(docs/claude/card-evidence-registry.json과 카드·워치리스트)를 읽는 테스트이며 이번 diff는 그 파일들도, 그 테스트가 부르는 코드도 건드리지 않는다. 기준선 실패로 보이지만 git 명령이 이 세션에서 막혀 수정 전 상태로 다시 돌려보지는 못했다(확인 필요 — 파이프라인 기준선 비교로 판정).
- `-p "test_auto_core_reconcile_outflow*"`: 38개 모두 OK(기존 28 + 새 10).
- 스키마 감사 `validate_schema_contracts.py`: PASS.
- 새 테스트와 지시문 항목:
  a `test_oct27_replay_passes_on_the_previous_trading_day_row`(173.64, basis base_after 2026-10-26, L −173.67, basis 키가 fallback 없을 때와 같음) ·
  b `test_base_after_row_present_is_used_even_with_a_fallback` ·
  c `test_fill_session_after_the_fallback_day_holds` ·
  d `test_failed_base_after_read_is_not_a_fallback_reason` ·
  e `test_two_base_after_usd_rows_hold` ·
  f `test_unusable_fallback_row_holds`(읽기 없음·행 없음·KRW 행만·USD 2행·값 불가·읽기 실패·fallback 키 없음) ·
  g `test_fallback_outside_the_ledger_days_holds`(10/19, 10/20, 10/27, 10/28) ·
  h `test_outflow_after_the_fallback_day_does_not_match`(NOT_MATCHED:−183.64:−173.67) ·
  i `test_limit_and_krw_rules_hold_on_the_fallback_row` ·
  j `FallbackRunTests.test_third_read_only_when_base_after_has_no_usd_row`: 합성 달력(10/12 마감을 기록 뒤로 둬서 before 10/09, after 10/13, 앞 세션 10/12). base_after 빈 응답이면 ust21132 요청 3번(20261009, 20261013, 20261012) 기록, 10/13 체결이 fallback 뒤라 `...:20261013:USD_ROW` 보류. base_after 행이 있으면 요청 2번, 통과.
- 실행에서 fallback으로 통과하는 경우는 기존 픽스처(체결 세션 = base_after)로는 만들 수 없어 단위 테스트 a에서만 확인했다.

## 반드시 적을 것
- (a) 이 변경은 증거 요건 완화(H2)다. `base_after` 행 없이도 I3가 통과할 수 있는 경로가 1개 생긴다(위 4조건이 모두 맞을 때). fallback 날짜 뒤~스냅숏 사이의 출금·입금은 스냅숏 잔차 R에는 들어가고 원장 잔차 L에는 안 들어가므로 |R−L| > 0.05가 되어 `UNVERIFIED_OUTFLOW_NOT_MATCHED`로 보류된다(테스트 h). 유입은 지금처럼 이 분기에 들어오지 않는다(R < −1.00일 때만 호출).
- (b) HWM 조정은 0 그대로다. 현금흐름 선언은 건드리지 않으므로 출금은 손실로 남는다.
- (c) 2026-10-28 06:15 결과는 병합 뒤 다음 실행(2026-10-29 06:15)에서 확인 필요. 그날 창에 base_after 세션(예: 10/28 미국 세션) 체결이 있으면 조건 3으로 계속 보류된다.
- (d) 겨울 시간(2026-11-01~) 영향은 확인 필요. 06:15 KST가 미국 마감 직후 15분이 되므로 base_after 행이 비는 날이 늘 수 있고, 그날 체결이 있으면 fallback으로도 보류된다.
- 주문·권한 표지: 표지 없음.

## 남은 위험
- KRW 행만 있고 USD 행이 없는 통과 응답도 "USD 0행"으로 본다(지시문 정의 그대로). 그 경우에도 fallback 행 정상·R–L 일치·한도·원화 증가 금지가 모두 필요하다.
- `previous_session`은 운영 달력의 세션 날짜만 본다. 달력이 틀리면 fallback 날짜도 틀리지만, 그 날짜 행이 정상이어야 하고 R–L 일치가 필요하므로 틀린 쪽은 보류다.
- 이 세션은 git 명령(diff·status)이 권한 거부로 막혀 diff를 직접 보지 못했다. 줄바꿈은 검색으로 확인했다: 고친 세 파일 모두 CR 없는 줄 0개.
- 커밋·병합·push 없음. 키움 호출·정책/상태/일지 쓰기 없음.
