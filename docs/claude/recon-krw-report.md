---
id: recon-krw-report
title: "B2-N 대조: 원화 예수금 증가 ₩1,000 이하 허용 — Builder 보고"
date: 2026-10-29
prompt: docs/claude/recon-krw-builder-prompt.md
class: "authority(K3, H2 제약 완화) — 병합은 사장 승인 + -ApproveAuthority"
---

## 바뀐 줄
- `manage-us-stock-strategy/scripts/auto_core_reconcile.py`
  - 101~103행: 주석 2줄 + 상수 `KRW_RISE_TOLERANCE = Decimal("1000")`(원). `OUTFLOW_MATCH_USD`(100행) 바로 아래.
  - 811~812행: `unverified_outflow` docstring의 원화 문장에 "base_before→base_after 증가 1000원 이하는 허용(recon-krw)" 추가.
  - 848행: 비교 한 줄 `balances[after]["won_entr"] > balances[before]["won_entr"]` →
    `balances[after]["won_entr"] - balances[before]["won_entr"] > KRW_RISE_TOLERANCE`.
    사유 문자열 `UNVERIFIED_OUTFLOW_KRW_DEPOSIT_ROSE:<before>:<after>`(849행), 결과 dict 키, `unverified_outflow_basis` 키는 그대로.
- `manage-us-stock-strategy/references/broker-snapshot-reconciliation.md` 306~308행: B2-N 설명의 "`won_entr` did not rise"를
  "base_before에서 base_after까지 1,000원 넘게 오르지 않음(1,000원 이하 증가는 허용, recon-krw 2026-10-29)"으로.
- `manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py` 590~643행: 새 클래스 `KrwRiseToleranceTests`만 추가. 기존 테스트 함수는 그대로.

## 상수와 비교 방식
- `KRW_RISE_TOLERANCE` = 1000원(Decimal). 증가분(after − before)이 1000을 **초과**할 때만 보류. 1000 정확히는 통과(경계 포함).
- 값 해석은 기존 `ledger_balance`의 `_decimal` 그대로라 해석 불가 값은 이전처럼 `...:VALUE`로 보류(fail-closed).
- 비교 기준은 base_before 대비 누적 증가라서 소액을 여러 번 나눠 입금해도 합이 1000을 넘으면 보류(테스트: 500→1501 보류).
- 검사 순서는 그대로: 창(SPAN) → 원장 읽기 → 0.05 일치 → 한도 → 원화. 원화 허용 때문에 다른 조건이 풀리지 않음.

## 대상 테스트
`PYTHONDONTWRITEBYTECODE=1`을 켜고 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"` 실행:
550개 실행, 실패 1, skip 1.
- 새 `KrwRiseToleranceTests` 7개(a 10-29 재현 ₩0→₩9 통과·출금액 "173.64"·basis 전체 비교, b 정확히 1000 통과, c 1001 보류,
  d 0→1,000,000 보류, e 감소·무변화 통과, f ₩9 증가 상태에서 0.05 불일치·한도·창 조건은 각각 기존 사유로 보류, 상수 값 확인) 모두 통과.
  기존 `test_krw_deposit_rise_holds`(0→120000 보류)와 fallback 원화 테스트도 그대로 통과.
- 실패 1: `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches`(symbol='PLTR') —
  `['CARD_SECTION_CHANGED', 'CARD_NOT_ACCEPTED_IN_WATCHLIST']`. 실제 카드 등록부·관심목록 자료를 읽는 테스트이고 이번 diff는 그
  파일들과 코드를 건드리지 않는다. 변경 전 기준선에서도 실패하는지는 이 세션에서 돌려 보지 않았다(확인 필요 — 파이프라인 기준선 비교로 판정).
- 줄바꿈: 고친 세 파일 모두 CRLF 유지(LF만 있는 줄 0).
- 주문·권한 줄: 표지 없음(바꾸거나 더한 것 없음).

## 남은 위험
- (a) 이 변경은 제약 완화(H2)다. 원화 ₩1,000 이하 증가는 환전 유입을 구분하는 데 쓰이지 않는다. ₩9의 출처가 외부 KRW
  입금(예: 소액 원화 입금)이었다면 허용이 맞지 않는 반례가 된다 — 출처는 확인 필요. 다만 금액 상한이 1,000원(약 $0.7)이라
  달러 쪽 0.05 일치·한도를 바꾸지 않고, 1,000원을 넘는 환전은 그대로 보류된다.
- (b) HWM 조정은 0 그대로다. 유입 인정·HWM 조정 코드를 더하지 않았고 `cash_flow_evidence.py`는 건드리지 않았다.
- (c) 2026-10-29 결과는 병합 뒤 다음 실행(10/30 06:15)에서 확인해야 한다. 원화 조건은 마지막 검사라, 10/29 보류 때 그 앞의
  0.05 일치·한도는 이미 통과한 상태였다. 다음 실행은 새 스냅숏·새 base_after로 이 조건들(0.05 일치·한도)을 다시 평가하므로 통과 여부는 확인 필요.
- (d) 겨울 시간(11/01~) 전환 뒤 base_before/base_after 날짜 선택(`ledger_days`, 운영 달력의 마감 시각)에 미치는 영향은 이번
  변경 범위 밖이며 확인 필요.
- 실행 제약: 허용 목록 밖 셸 작업(줄바꿈 해시 점검 등)은 권한 때문에 막혀서, 줄바꿈 확인은 검색 도구로 했다.
