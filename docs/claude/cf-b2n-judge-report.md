---
id: cf-b2n-judge-report
title: "cf-b2n(B2-N) 독립 Judge 보고 (읽기 전용, Opus xhigh, Read·Grep·Glob)"
date: "2026-10-25"
verdict: "PASS (1차 10:3x PASS → Cowork 발견 won_entr 위치 결함 → 최소 수정 2회 → 2차 11:2x PASS, 막는 문제 0)"
source: "workspace/outputs/dev-runs/cf-b2n/judge-1.json (원문 옮김)"
---

## 1차 뒤 Cowork 발견 (2026-10-25 10:5x)
- 실제 ust21132 응답은 won_entr를 본문 최상위에 둔다(2026-10-23 실조회·사양 depth 0). 브리지는 result_list 행만 옮기므로 행의 won_entr는 늘 None → 운영에서 B2-N이 한 번도 통과 못 함(fail-closed라 안전, 기능은 죽음). 시험 픽스처가 행 안에 won_entr를 넣어 가렸다. Judge 발견 3("USD 행에 won_entr가 오는지 미확인")과 같은 지점. → Builder 최소 수정 2회(fix-2-prompt.md) 후 변경분 재판정.

## 1차 Judge 원문
# Judge 판정 — cf-b2n (B2-N), 읽기 전용

**결론: 막는 문제는 없고, PASS입니다.** 아래 항목 1~6을 모두 이 세션에서 원문 파일을 열어 확인했습니다. 수정은 하지 않았습니다.

## 항목별 판정

### 1. diff 범위 — **PASS**
- **바뀐 파일:** `diff.patch`의 `diff --git` 6개(redesign 문서, reference 문서, `auto_core_reconcile.py`, `kiwoom_account_readonly_bridge.py`, 고정 시험 2개)와 커밋 안 된 새 파일 2개(새 시험 파일, 보고서)뿐입니다. 고정 시험 2개는 fix-1 지시로 허용된 파일입니다.
- **예외 분기와 보조 함수:** 상수 `auto_core_reconcile.py:97-102`, 보조 함수 `:730-819`, 분기 `:890-896`, 결과 필드 `:906`, 경고 `:1246-1248`·`:1253`.
- **브리지 조회 추가:** `kiwoom_account_readonly_bridge.py:33`·`:51`·`:58`·`:99`.
  - I1에는 들어가지 않았습니다. I1은 `expected + needed`만 검사하고(`:1131-1132`), `dated_requests`(`:208-213`)와 `I1_SNAPSHOT_OPERATIONS`(`:65-66`)도 그대로입니다.
- **바뀌지 않은 것:**
  - `cash_flow_evidence.py`는 diff에 없습니다.
  - `CASH_TOLERANCE_USD`=1.00(`:67`), `FILL_WINDOW_MAXIMUM_DAYS`=14(`:83`), `plan_reads`(`:195-205`), `invariant_i1`(`:232-249`), 정산 함수(`:437-616`), I4·I5(`:988-1017`)를 건드린 hunk는 없습니다.
- **문서 두 곳:**
  - `automation-redesign-2026-10-10.md:111`의 추가 문장은 지시문 문장과 글자까지 같습니다.
  - reference 문서는 `:228`(I3 표)과 `:282-303`(본문)에 같은 내용이 들어갔습니다.
- **고정 시험 2개:** 허용된 줄만 바뀌었습니다(`test_reconcile_broker_state.py:178`·`:181`, `test_kiwoom_account_bodies.py:27`).

### 2. 2a~2g 모두 충족할 때만 예외 적용 — **PASS**
- **조건별 코드 위치:**
  - 2a 유출만: `difference < -CASH_TOLERANCE_USD`(`:891`)
  - 2b 다른 I3 사유 없음: 사유 목록이 `CASH_CHANGE_NOT_EXPLAINED` 한 개와 정확히 같아야 함(`:892`). D0 경우에는 이 사유가 아예 생기지 않습니다(`:879-887`).
  - 2c 원장 두 날짜: `:740-775`·`:799-804`. "내역 없음"은 ust21132에 빈 PASS 승격 규칙이 없어(`bridge.py:119-129`) 실패로 남습니다.
  - 2d 체결 구간: `:795-798`
  - 2e L 일치: `:805-807`
  - 2f 기준 주문가능액 이하: `:808-810`
  - 2g 원화 예수금 증가 없음: `:811-812`
- 통과할 때만 사유를 비웁니다(`:896`). 그 밖에는 기존 사유 뒤에 B2-N 사유를 붙여 HOLD합니다.
- **유입은 인정되지 않습니다.** `:891`에서 막히고 L ≥ −1도 HOLD입니다(`:806`).
- **조건별 시험(새 시험 파일):**

| 조건 | 시험 위치 |
|---|---|
| 2a 유입 | `:280-288` |
| 2b 다른 I3 사유 | `:344-349`(미체결, R −82.93) |
| 2c 원장 조회 불가 | `:194-226`, `:301-333` |
| 2d 구간 밖 체결 | `:179-183` |
| 2e 0.05는 통과·0.06은 HOLD, L ≥ −1 | `:168-177` |
| 2f 기준 현금 초과 | `:185-187` |
| 2g 원화 증가 | `:189-192`, `:351-355` |
| 10-23 재현 | `:132-144` |

### 3. HWM 조정 없음 — **PASS**
- 신고 블록은 `NO_EXTERNAL_FLOW`, declared 0입니다(`cash_flow_evidence.py:299-300`, `:316`).
- HWM 조정은 `hwm_adjustment_usd`가 0이 아닐 때만 생깁니다(`:415-418`). HWM 갱신 경로는 `portfolio_exposure.py:714-718`입니다.
- 지분은 보유×종가 + 스냅숏 현금으로 계산됩니다(`portfolio_exposure.py:373-399`).
- 따라서 기록된 현금이 82.93 줄면 지분도 그만큼 줄고 HWM은 그대로입니다. **출금은 손실로 남습니다.**
- 시험 확인: 신고 `NO_EXTERNAL_FLOW`와 hwm 동일(`:251-254`), apply 원장 `new_external_net_usd` 0.00(`:263-264`).
- apply 경로는 I3 status만 확인하고(`apply_user_confirmed_broker_snapshot.py:423-426`) I3 블록을 원장에 그대로 넣습니다(`:478`). 스키마도 추가 필드를 막지 않습니다(`auto-core-result.schema.json:32`).

### 4. 새 조회 조건과 실패 처리 — **PASS**
- **|R| ≤ 1이면 조회하지 않습니다.** 시험 `:269-278`이 R = 0, −1.00, +1.00에서 ust21132 조회 0건, 달력 호출 0건을 확인합니다.
- **실패는 모두 HOLD이고 실행을 끝내는 예외가 아닙니다.**
  - 달력 예외: `CloseHistoryError`·`IntegratedAuthorityLoadError`·`SessionCalendarLoadError`가 모두 `ValueError` 하위입니다. 로더 실패도 `ValueError`로 바뀝니다(`auto_core_reconcile.py:736`).
  - 조회기 예외: `BridgeError`가 `RuntimeError` 하위입니다(`kiwoom_runtime_bridge.py:56`).
  - 두 예외 모두 `outflow_ledger`가 잡아 사유로 돌려줍니다(`:1174-1175`, `:1182-1183`).
  - 시험: `:301-333`.

### 5. 권한 줄·매도 차단·허용 파일·줄바꿈·전체 시험 — **PASS**
- **권한 줄:** diff의 +/− 줄에 `order_authority`, `quantity_authority`, `execution_quantity`, `kill_switch`, `ORDER_TICKET_HUMAN_ENTRY`가 없습니다(Grep 0건). 반환값의 권한 필드(`:1268-1269`)도 그대로입니다.
- **매도 차단 추가 없음:** 새 분기는 이미 HOLD인 경우(I3 사유가 있는 경우)에만 돌아서, HOLD를 OK로 바꿀 수만 있고 새 HOLD를 만들지 않습니다.
- **줄바꿈:** 기존 파일 6개는 LF만 있는 줄이 0개로 CRLF 그대로입니다(`auto_core_reconcile.py` CR 줄 1397개, 브리지 514개, redesign 문서 243개, reference 문서 348개, 고정 시험 2개).
- **전체 시험:** 기준선 3295개, 이후 3317개로, 차이 22개는 새 파일의 시험 수와 같습니다. 실패·오류는 양쪽 모두 failures=22, errors=9로 같은 이름 31개입니다(`tests-base.txt:445-447`, `tests-after.txt:445-447`, `fail-compare.txt:1-3`: 새로 생긴 것·사라진 것 모두 없음).
- **읽기 전용 경로 시험:** `test_reconcile_broker_state.py:182-185`가 `ACCOUNT_APIS.values()` 전체를 돌므로 ust21132도 검사 대상입니다.

### 6. 보고서 — **PASS**
- 필수 항목 (a)~(e)가 모두 있습니다(`cf-b2n-report.md:127-131`).
- 정책 파일 판단도 있습니다(`:122-124`): 실행에는 정책 변경이 필요 없습니다.
  - 확인: `allowed_api_targets`를 읽는 코드는 `kiwoom_candidate_discovery_bridge.py:27`뿐입니다.
  - 계좌 브리지는 코드의 `ACCOUNT_APIS`만 씁니다(`bridge.py:217-219`).

## 발견 사항

**막는 문제: 없음**

**막지 않는 문제:**
1. **시험 주석 하나가 틀렸습니다(`test_auto_core_reconcile_outflow.py:336`).** FILL_AMOUNT_UNAVAILABLE 경우는 체결 금액이 0이 되어(`auto_core_reconcile.py:551-553`) R = 1246.24 − 1000.00 = **+246.24**, 즉 유입입니다. 그래서 이 경우는 2b가 아니라 2a에서 막히고, "잔차도 유출"이라는 주석은 사실과 다릅니다. 보고서 `:70`도 같은 부분을 과하게 적었습니다.
   - 2b 자체는 같은 시험의 미체결 경우(R −82.93)가 따로 증명하고, 코드(`:892`)는 목록이 정확히 같은지 비교하므로 동작은 맞습니다.
   - 권고: 나중에 일반 변경으로 순매수 시험 데이터(R < 0 이면서 FILL_AMOUNT_UNAVAILABLE)로 바꿉니다.
2. **새 시험 파일만 LF입니다.** tests 폴더에서 CRLF가 아닌 유일한 파일입니다. 기존 줄바꿈을 바꾼 것은 아닙니다. 보고서는 "색인은 모두 LF라 커밋 결과가 같다"고 하지만, 저는 git을 쓸 수 없어 확인하지 못했습니다(확인 필요).
3. **실측 전 부분이 있습니다.** ust21132 요청 본문 `{"base_dt": ""}`, USD 행에 `won_entr`가 오는지, 06:15에 직전 거래일 값이 있는지는 아직 실제로 확인되지 않았습니다. 셋 다 틀리면 HOLD로 끝나므로(fail-closed) 안전하고, 첫 실행의 I3 사유로 바로 보입니다. 보고서 (d)에 적혀 있습니다.
4. **이론상 남는 경우 하나.** `ledger_balance`는 `outflow_ledger`의 예외 처리 밖에서 실행되므로, 조회기가 dict가 아닌 결과를 주면 HOLD가 아니라 실행 실패(FAIL)가 됩니다. 실제 브리지는 항상 dict를 돌려주므로(`bridge.py:435-443`) 실제로 생길 일은 아닙니다. FAIL이어도 아무것도 쓰지 않습니다.
5. **선택 사항.** 문서 정합성을 위해 `kiwoom-broker-readonly-policy.json`의 `allowed_api_targets`에 ust21132를 추가하는 안은 실행에 영향이 없습니다. 하려면 사장 승인 뒤 Cowork가 합니다.

VERDICT: PASS

## 2차 Judge 원문 (변경분, 2026-10-25 11:2x KST)
**결론: 1차 이후 바뀐 부분에 막는 문제는 없습니다. 판정은 PASS입니다.** 이 세션에서 원문 파일을 직접 열어 확인했고, 파일은 하나도 고치지 않았습니다. 시험은 직접 돌리지 못해서 5번 시험 결과는 보고서 기록을 근거로 했습니다.

## 항목별 판정

### 1. 브리지 수정 범위 — **PASS**
- **바뀐 곳:** `kiwoom_account_readonly_bridge.py:303-308` 한 군데입니다.
  - 각 페이지의 행을 `page_rows`로 만듭니다.
  - `operation == "account_deposit_by_date_read"`일 때만 각 행의 `won_entr`를 `response.body.get("won_entr")`로 덮어씁니다(`:304-307`).
- **행 안의 `won_entr`는 쓰지 않습니다.** `:303`에서 행 값을 먼저 옮기지만 `:307`이 본문 최상위 값으로 덮어씁니다. 최상위에 없으면 `.get`이 None을 줍니다.
- **다른 조작·필드는 그대로입니다.**
  - 조건문이 ust21132에만 걸립니다.
  - `SAFE_FIELDS`(`:99`), `ACCOUNT_APIS`(`:33`), 본문 틀(`:51`), `DATED_PARAMETERS`(`:58`)는 1차와 같습니다.
  - 그 밖의 최상위 칸(`tot_evlt_amt`, 계좌번호가 섞일 수 있는 `return_msg`)은 옮기지 않습니다.
  - 부모 쪽 `_sanitize`(`:406`)도 그대로 `SAFE_FIELDS`만 남깁니다.
- **새 네트워크·쓰기 경로가 없습니다.** 추가된 줄은 메모리 안의 dict만 다룹니다. 조회 경로는 계속 `ACCOUNT_APIS`의 `/api/us/acnt` 하나이고, 읽기 전용 시험(`test_reconcile_broker_state.py:177-186`)도 그대로입니다.

### 2. won_entr가 없거나 못 읽으면 HOLD, 10-23 재현은 통과 — **PASS**
- **못 읽으면 HOLD로 끝납니다.**
  - `_decimal`은 None과 읽을 수 없는 문자열이면 None을 줍니다(`auto_core_reconcile.py:114-121`).
  - 그러면 `ledger_balance`가 `…:<YYYYMMDD>:VALUE`를 돌려줍니다(`:772-774`).
  - `unverified_outflow`는 바로 그 사유로 끝나고(`:801-803`), `explain_change`가 사유를 붙여 I3 FAIL이 됩니다(`:896`, `:900`).
  - 시험: `test_auto_core_reconcile_outflow.py:209-211`(행 값 None), `:405-411`(브리지 단계에서 최상위가 없는 경우).
- **"000000000000"은 0으로 읽힙니다.** `Decimal("000000000000")`은 0입니다. 브리지 시험 `:403`이 `won_entr Decimal("0")`을 확인합니다.
- **10-23 재현은 그대로 통과합니다.** `:134-146`은 두 날짜 모두 `won_entr "0"`으로 I3 PASS, 82.93, `won_entr_before/after "0"`을 확인합니다. `auto_core_reconcile.py`는 1차 뒤 바뀌지 않았습니다(4번 참고).

### 3. 새 브리지 시험과 주석 정정 — **PASS**
- **가짜 client를 씁니다.** `:387-393`에서 `SimpleNamespace(fetch_page=mock.Mock(...))`와 `pacer=mock.Mock()`으로 `bridge._read_pages`를 부릅니다. 키움 호출은 없습니다.
  - 응답 본문은 `return_code` 0이라 검사를 통과합니다(`bridge.py:155-161`).
  - 다음 페이지 표시 `{"cont_yn":"N"}`로 한 페이지에서 끝납니다(`kiwoom_runtime_bridge.py:242-246`, `bridge.py:334-336`).
- **실제 응답 모양과 같습니다.** `:397-399`는 최상위에 `won_entr "000000000000"`·`tot_evlt_amt`·`return_code 0`을 두고, 행에는 crnc_code·fx_entr·evlt_amt·crnc_rt·chg_entr·chg_evlt_amt·evlt_amt_wght만 둡니다. 행에는 won_entr가 없습니다. fix-2 지시문(`fix-2-prompt.md:3`)에 인용된 10-23 실조회 모양과 칸이 같습니다. 값은 합성 값입니다.
- **확인 내용:**
  - 행에 최상위 값이 붙습니다(`:401`).
  - 최상위에 없으면 행 안의 "5"를 무시하고 None이 됩니다(`:409`).
  - 다른 조작(`account_deposit_read`)에는 최상위 값이 붙지 않습니다(`:413-416`).
- **주석 정정(`:338-339`)은 사실과 맞습니다.**
  - 당일매매 행이 없으면 `FILL_AMOUNT_UNAVAILABLE`이 납니다(`auto_core_reconcile.py:383-384`).
  - 그러면 `fill_settlement`가 체결 금액 0을 돌려줍니다(`:551-553`).
  - 픽스처는 기준 현금 + 흐름이 1000.00입니다(`test:71-73`의 R = 1246.24 − 1000.00 − 329.17 = −82.93). 따라서 R = 1246.24 − 1000.00 = **+246.24**, 즉 유입입니다.
  - 유입은 2a 조건 `difference < -CASH_TOLERANCE_USD`(`:891`)에서 걸러져 분기에 들어가지 않습니다.
  - 2b 자체는 미체결 경우(`test:347-352`)가 따로 보여 줍니다.

### 4. 1차 이후 다른 변경 없음, 1차 항목 1~6 유지, 권한 줄 없음, 줄바꿈 — **PASS**
- **바뀐 파일:** 세션 시작 때 git 상태가 1차와 같은 수정 6개 + 새 파일 2개뿐입니다. fix-2가 손댄 파일은 허용된 3개(브리지, 새 시험, 보고서)입니다.
- **`auto_core_reconcile.py`는 바뀌지 않았습니다.**
  - CR 줄 수가 1397개로 1차와 같습니다.
  - 1차 Judge가 인용한 줄이 그대로 같은 코드를 가리킵니다: `:97-102`, `:730-819`, `:890-896`, `:906`, `:1174-1175`, `:1182-1183`, `:1246-1248`, `:1253`, `:1268-1269`.
- **브리지는 `_read_pages`만 늘었습니다.**
  - CR 줄이 514에서 519로 정확히 5줄 늘었고(LF만 있는 줄 0), 1줄이 6줄이 된 것과 맞습니다.
  - 앞쪽 인용 줄(`:33`, `:51`, `:58`, `:99`, `:119-129`, `:217-219`)은 그대로이고, 1차 `:435-443`은 지금 `:440-448`로 5줄 밀렸습니다.
- **문서 두 개와 고정 시험 두 개도 그대로입니다.**
  - 줄 수: redesign 문서 243, reference 문서 348로 같습니다.
  - 고정 시험 두 개는 CRLF 그대로이고, 허용된 줄만 1차 때와 같습니다(`test_reconcile_broker_state.py:178`·`:181`, `test_kiwoom_account_bodies.py:27`).
- **새 시험 파일은 보고된 곳만 바뀐 것으로 보입니다.** 1차 인용 줄과 비교하면 줄 밀림이 +1(`:18` import), +2(`:46` 주석), +3(`:338-339` 두 줄 주석)으로 정확히 맞습니다. 그 뒤에 새 시험 2개(`:387-416`)가 붙었습니다. 시험 수는 3+7+10+4 = 24개입니다. 이 파일은 이전처럼 LF입니다(CR 줄 0).
- **보고서:** 1차 인용 줄(`:70`, `:122-124`, `:127-131`)이 그대로이고 8절(`:166-179`)만 추가됐습니다.
- **권한 줄:** diff.patch의 +/− 줄에 `order_authority`, `quantity_authority`, `execution_quantity`, `kill_switch`, `ORDER_TICKET_HUMAN_ENTRY`, `decision_mode`가 없습니다(검색 0건). 새 시험 파일에서는 `:264` 한 곳만 나오는데, 기존 값 `AUTO_CORE_INVARIANTS`를 확인하는 줄로 1차 때부터 있었습니다.

### 5. 전체 시험 — **PASS (보고서 기준)**
- **수:** 보고서 `:177`에 Ran 3319, failures=22, errors=9가 적혀 있습니다. 기준선 3295(`tests-base.txt:445`)에 새 파일 24개를 더하면 3319로 맞습니다.
- **이름:** 기준선 실패·오류 31개(`tests-base.txt:4-433`: ERROR 9, FAIL 22)와 보고서 7절 목록(`:145-163`)·8절 묶음(`:177`)이 모듈·개수 모두 같습니다. 1차 비교(`fail-compare.txt:1-3`)에서도 새로 생긴 것·사라진 것이 없었습니다.
- **한계:** 3319개 실행의 원본 로그는 judge-input에 없습니다. 그래서 2차 실행 수치는 보고서 원문만 근거입니다(확인 필요). 다만 2차에서 바뀐 것은 브리지 한 곳과 새 시험뿐이라 다른 시험에 영향이 갈 경로는 보이지 않습니다.

## 발견 사항

**막는 문제: 없음**

**막지 않는 문제:**
1. **보고서 4-1절(`cf-b2n-report.md:70`)은 고치지 않았습니다.** 1차에서 지적한 과장된 표현이 남아 있지만, 8절(`:170`)이 정정 내용을 적고 있어 사실 관계는 맞습니다. 1차 권고(순매수 픽스처로 R < 0 이면서 `FILL_AMOUNT_UNAVAILABLE`인 경우를 따로 시험)도 아직 남아 있습니다. 이번 지시 범위(주석만) 밖입니다.
2. **새 브리지 시험은 `fetch_page`에 넘긴 TR 번호(ust21132)를 확인하지 않습니다.** 경로 자체는 `test_ust21132_is_a_dated_read_only_inquiry`(`:369-385`)와 읽기 전용 시험이 따로 확인합니다.
3. **아직 실측 전인 부분이 하나 더 있습니다.** 원화 잔액이 0이 아닐 때 `won_entr`의 실제 표기(부호·소수점)는 아직 실조회로 본 적이 없습니다. 못 읽으면 `:VALUE` HOLD라 안전 쪽으로 실패하고, 1차 발견 3번(본문 틀, 06:15 시점 값)과 같은 첫 실행에서 드러납니다.
4. **2차 전체 시험의 원본 로그가 없습니다.** 5번에 적은 대로 보고서 수치만 근거입니다.

VERDICT: PASS

