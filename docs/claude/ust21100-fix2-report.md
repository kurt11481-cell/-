---
id: ust21100-fix2-report
title: ust21100(미국주식 거래내역) 요청 본문 krw_repl_skip_yn "" → "N" — Builder 보고
date: 2026-10-13
source: docs/claude/ust21100-fix2-builder-prompt.md
authority: order_authority=false · quantity_authority 변경 없음 · 주문 경로 없음 · 키움 호출 없음 · 정책·상태 파일 무변경
---

## 바꾼 줄

`manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py` `ACCOUNT_BODIES["account_transaction_history_read"]` (CRLF 유지, ASCII)

```diff
+    # ust21100 live 2026-10-13: the server treats tp and krw_repl_skip_yn as required (empty -> 1511);
+    # "N" = KRW substitute in/out not excluded (all included), the kiwoomcli default.
     "account_transaction_history_read": {"strt_dt": "", "end_dt": "", "tp": "0", "stex_tp": "", "stk_cd": "",
-                                         "krw_repl_skip_yn": ""},
+                                         "krw_repl_skip_yn": "N"},
```

그 밖의 칸, 다른 조회 본문, ACCOUNT_APIS, DATED_PARAMETERS, SAFE_FIELDS, NO_DATA_* 표, 검증 함수, 워커 흐름은 바꾸지 않았다. "추가 실측" 절은 "해당 없음"이라 1~2만 적용했다.

## 새 테스트 — `manage-us-stock-strategy/tests/test_kiwoom_account_bodies.py` (3개)

- `test_transaction_history_required_fields_are_filled`: tp == "0", krw_repl_skip_yn == "N"(빈 값 아님), 템플릿 전체가 고정 dict와 같음. 수정을 되돌려 ""로 바꾸면 실패한다.
- `test_transaction_history_request_body_fills_dates_only`: `request_body(validate_request(... 20261010~20261013))`가 날짜 두 칸만 채운 템플릿과 같고, 템플릿 자체는 바뀌지 않음.
- `test_other_bodies_unchanged`: 나머지 8개 조회 본문(account_deposit_read … account_day_trades_read)이 변경 전 값(골든 dict)과 같고, 조회 집합에 다른 항목이 더해지지 않음.

키움을 부르는 테스트는 없다.

## 대상 테스트 결과

| 패턴 | Ran | 결과 |
|---|---|---|
| test_kiwoom_account_bodies*.py | 3 | OK |
| test_s1b*.py | 50 | OK |
| test_broker_visibility_audit*.py | 3 | OK |
| test_kiwoom_broker_shadow*.py | 24 | OK |
| test_reconcile_broker_state*.py | 56 | OK |
| test_auto_core*.py | 324 | OK (skipped=1, 이번 변경과 무관한 기존 skip) |

기존 테스트 파일은 고치지 않았다.

## 남은 위험

- 서버가 다른 칸을 숨은 필수로 다룰 수 있다. 실측(2026-10-13 10:26 KST)으로 확인한 범위는 tp·krw_repl_skip_yn 두 칸이며, stex_tp·stk_cd 빈 값은 통과했다. "N" 본문의 실측 응답은 기간 내 내역 없음(20, 501724)이었으므로, 행이 있는 기간의 응답 필드(SAFE_FIELDS) 일치는 다음 실제 daily 실행에서 확인된다. 다른 칸이 막히면 I1이 이전처럼 KIWOOM_API_RESPONSE_ERROR로 멈추고(fail-closed) 상태는 바뀌지 않는다.
- "N"(원화대용입출금 비제외)은 S7 U3 실측과 cash_flow_evidence가 전제한 조회와 같지만, 원화대용 행이 실제로 섞여 나오면 소비자(cash_flow_evidence)가 그 행을 어떻게 분류하는지는 이 변경 범위 밖이다.
