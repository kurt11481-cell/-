---
id: swing-k3-builder-prompt
title: "스윙 실전 종목 상품 승인 넓히기(PLTR·CRWD) + 원본 상품 등록부 정리 — 수동 경로 Builder 지시문(초안)"
date: 2026-11-20
status: "초안 — 착수 전. 수동 경로(정책·등록부는 개발 큐 보호 경로라 dev-run 불가 — tools/dev_pipeline/README.md 보호 경로 P6 `workspace/policies/**`·`stock-strategy-system/**`, 선례 qqq-reg). 착수 = 별도 사장 결정 카드, 권한 자리 차례(cal-2027 → 정책 묶음 A 뒤, active-decisions.md 144행)에만"
class: "authority(K3 — 상품 승인·상품 등록부·정책). 수동 경로: Builder Opus(worktree swing-k3) → 별도 읽기 전용 Judge(Opus) → 병합은 사장 결정 + 사장 PowerShell 병합 스크립트 docs/claude/swing-k3-merge-<날짜>.ps1(qqq-reg 선례)"
allowed_files: "workspace/policies/instrument_registry.json · stock-strategy-system/alert_policy.json · manage-us-stock-strategy/scripts/auto_core_tickets.py · manage-us-stock-strategy/tests/test_swing_k3_registration.py(새로) · manage-us-stock-strategy/tests/test_portfolio_exposure.py(105~107·112행 기대값만) · manage-us-stock-strategy/tests/test_qqq_registration.py(34행 상수 이름·77행 기대값만) · docs/claude/swing-k3-report.md"
source: "사장 결정 카드 2026-11-20 15:39:42 KST 'PLTR·CRWD+등록부 정리'(cmsg_0137MRzn9nuDvvQmVxm6WeX9MtfKVr9UJDdDuor4zcUGZP) — docs/claude/swing-product-approval-k3-2026-11-20.md 4·7절 · active-decisions.md swing-k3-1120 행. 선례: qqq-reg(2b9afc9) · product-approval-PWR-LITE-2026-10-08.md 5절 ④"
crwd_condition: "CRWD 관심 카드 v1 수락 2026-11-20 15:59:32 KST(사장 결정 카드, active-decisions.md crwd-card-1120 행, watch-card-CRWD-2026-11-20.md) — CRWD 포함. 착수 때 그 행이 있는지만 다시 확인한다"
crwd_split_note: "CRWD 2026-07-02 4:1 분할 공식 기록이 corporate-actions.json에 없어 코어가 SPLIT_SUSPECTED:CRWD:2026-07-02로 CRWD 주문표를 막는다(근거 SEC 8-K 2026-06-03 Item 8.01). 이 지시문 범위 밖 — 분할 기록은 별도 경로. 승인 뒤에도 그 기록 전까지 CRWD 코어 주문표는 없다(보고 남은 위험에 적음)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 상태·일지·원장·예약 쓰기 없음"
weekly_user_touch: "1 (병합: 사장 PowerShell로 병합 스크립트 1번)"
---

## 목표
1. 사장이 2026-11-20에 고른 범위대로 PLTR·CRWD를 신규 매수 승인 상품에 넣는다(코드 목록·정책 배수·카드 핵심).
2. 원본 상품 등록부(workspace/policies/instrument_registry.json)에 승인 상품인데 기록이 없는 6종목(LITE·PWR·MU·DELL·AMD·TQQQ)과 PLTR·CRWD의 신원을 공식 출처로 검증해 적는다. → 2026-11-06부터 매일 나는 `POST_APPLY_CHECK_ERROR:LITE: canonical instrument registry record is missing or unverified`(reconcile_broker_state.py 108~122행)가 사라져야 한다.

## 바꿀 내용

### A. workspace/policies/instrument_registry.json (`instruments`)
- 새 항목 LITE·PWR·MU·DELL·AMD(보통주)·TQQQ(3배 레버리지 ETF), 기존 항목 PLTR·CRWD 갱신. 형식은 NOW·QQQ 항목(legal_issuer_name·instrument_type·security_class·exchange·trading_currency·identity_status "verified_primary_source"·identity_verification_status "VERIFIED"·official_identity_source_url·official_identity_source_type·identity_verified_at(KST)·leverage_factor·leverage_factor_status)을 따른다. TQQQ는 QQQ 항목의 신원 필드(legal_issuer_name·official_identity_source_url 등) + SOXL 항목의 레버리지 필드(leveraged_etf·leverage_factor 3·daily_target_multiple 3·confirmation_proxy QQQ)로 쓴다.
- 신원 출처(Builder가 웹을 못 열면 그 종목은 BLOCKED — 확인 필요): SEC EDGAR 최신 10-K(ETF는 운용사 공식 페이지 또는 SEC 485BPOS) 원문. 종목마다 URL·확인 시각을 보고에 적는다. **확인 못 한 종목은 넣지 않고 BLOCKED 표에 적는다**(가정 금지). CRWD는 2026-07-01 무렵 4:1 분할 — 신원 기록과 무관하지만 보고에 SEC 원문 확인 결과를 적는다.
- 필드 값(행동이 바뀌지 않게):
  - `new_buy_instrument_approved`: **모든 항목 false 그대로**(승인은 auto_core_tickets.py APPROVED_BUY와 통합 점검 목록으로 운영. true로 바꾸면 validate_decision_record.py 278행 등 관문이 달라짐 — 이번 범위 밖).
  - `short_sale_approved` false, `confirmation_proxy` 보통주 null.
  - `watchlist_approved`·`candidate_status`·`portfolio_bucket`: 먼저 이 필드를 읽는 코드(screen_tactical_candidates.py 65·85행, run_tactical_opportunity_radar.py 46·266·314행, validate_decision_record.py 178~195행, portfolio_decision_order_intent.py 46행, portfolio_decision_dashboard.py 2498행, shadow_acceptance.py 219행, holding_baseline_operationalization.py 41행, complete_holding_event_coverage.py 78행)를 읽고, 각 값이 어떤 실행 경로를 새로 여는지 표로 보고한다. **새 경로를 여는 값이면 닫힌 쪽(false·inactive)을 고른다.** PLTR·CRWD의 지금 값(watchlist_approved false · candidate_status inactive · historical_research_registry)도 같은 기준으로 판단하고 바꾼 이유를 적는다.
- 다른 항목·키·순서·들여쓰기는 바꾸지 않는다. `registry_version`은 새 값(예 "2026-11-2x-swing-k3-instrument-registry-v1")으로.
- `stock-strategy-system/alert_policy.json`의 `decision_harness.instrument_registry_authority.required_canonical_sha256`을 validate_registry_consistency.canonical_hash로 다시 계산한 값으로(이 키 하나만). 정책 사본 `decision_harness.instrument_registry`는 건드리지 않는다.

### B. stock-strategy-system/alert_policy.json (`portfolio_exposure_policy`)
- `nominal_multipliers`에 `"PLTR": 1`, `"CRWD": 1`을 `"QQQ": 1` 앞에(한 줄 객체 형식 유지).
- `card_stock_core`에 PLTR·CRWD를 끝에 더한다.
- 그 밖(add_default·allowed_index_etfs·문턱·single_stock_*·instrument_approval_gate)은 그대로.
- card_stock_core에 들면 실적 금지 구간 판정 대상이 된다(portfolio_exposure.py 1216행). PLTR·CRWD는 earnings-anchors.json에 있음 — 실적일 자료가 없을 때 매수가 막히는지 코드로 확인해 보고한다.

### C. manage-us-stock-strategy/scripts/auto_core_tickets.py
- 61행 주석과 `APPROVED_BUY`에 PLTR·CRWD를 더한다(주석: "PLTR, CRWD: user approval 2026-11-20 swing-k3-1120"). ASCII만.
- `ONE_X_UNREGISTERED`는 바꾸지 않는다. PWR·LITE가 이제 정책 배수에 있어 이 목록이 쓰이는지(177~178행) 보고에만 적는다.

### D. 새 테스트 manage-us-stock-strategy/tests/test_swing_k3_registration.py (이 파일만 새로)
  a. 실제 instrument_registry.json: 8종목(CRWD 조건 무관) identity_status가 "verified"로 시작, 모든 항목 new_buy_instrument_approved false.
  b. 실제 두 파일로 validate_registry_consistency가 해시 오류 없음.
  c. 실제 alert_policy.json: PLTR·CRWD 배수 1·card_stock_core 포함, hard_ceiling 1.9·target 1.55·reduce 1.85·single_stock_nominal_cap 0.4 그대로, 기존 card_stock_core 7종목 순서 그대로.
  d. APPROVED_BUY = 기존 10개 + PLTR·CRWD, INDEX_ETFS·PARKING_ETFS 그대로.
  e. reconcile_broker_state.alert_engine_check(가상 보유 BE·LITE·SOXL, 실제 등록부 경로): `canonical instrument registry record is missing or unverified` 오류 없음.
  f. 대조: 등록 안 된 기호(예 "XLE")는 여전히 portfolio_exposure 매수 자격에서 막힘, 승인 밖 개별주(예 "NOW")는 APPROVED_BUY에 없음.
- CRWD를 뺀 경우 c·d·e의 기대값에서 CRWD만 뺀다.

## 테스트
- 기존 테스트 가운데 정책 값을 통째로 고정한 곳만 고친다: test_portfolio_exposure.py 105~107행(배수 dict에 PLTR·CRWD)·112행(card_stock_core), test_qqq_registration.py 34·77행(QQQ 등록 때의 '바꾸기 전' 고정 — 상수를 그대로 두고 77행 비교를 '앞 7종목이 그 상수와 같다'로). 그 밖에 바뀌어야 통과하는 기존 테스트가 있으면 멈추고 docs/claude/swing-k3-BLOCKED.md에 적는다.
- 실행은 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"` 형식 그대로 — 패턴 `test_swing_k3_registration.py`·`test_portfolio_exposure*.py`·`test_qqq_registration.py`·`test_auto_core*.py`·`test_reconcile_broker_state.py`, 그리고 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`. 앞에 환경 변수·옵션을 붙이지 않는다. 전체 테스트는 파이프라인이 돌린다. 기준선에서 이미 실패하던 테스트(PLTR 등록부 해시 등 — baseline-failure 기록)는 고치지 않고 보고에 이름만 적는다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. 실행 금지: auto_core.py·"auto_core.py"가 든 명령·reconcile apply·kiwoomcli·키움 호출·run_auto_core.ps1. 상태(portfolio_state.json)·런타임·일지·원장·예약 작업·대시보드 쓰기 없음.
2. 권한 표지 줄(order_authority·quantity_authority·execution_quantity·kill_switch·hard_ceiling) 무변경, 주문 경로 문자열(`/api/us/ordr`, `ust2000x`, `kiwoom_order`, `order_submit`) 없음, schemas/ 무변경.
3. 허용 파일(머리말 allowed_files)만. 세 파일 모두 git i/lf · 작업 트리 CRLF — 줄바꿈 유지. scripts/*.py ASCII 전용.
4. 통합 점검 규칙·예약 지시문은 바꾸지 않는다(134행 목록 변경은 병합 뒤 `예약 작업 변경 승인: 보유·관심 종목 통합 점검` 경로로 따로).
5. git commit·push·병합 없음(바뀐 파일은 worktree에 커밋하지 않은 채 둔다 — 병합 스크립트가 해시 확인 뒤 커밋, qqq-reg 선례).

## 보고 docs/claude/swing-k3-report.md
첫 줄에 CRWD 포함 여부와 근거 행. 바뀐 줄(파일:행, 앞뒤 값) · 종목별 신원 출처 URL·확인 시각 · A의 필드 소비자 표와 고른 값의 이유 · 테스트 결과(Ran 수·실패 0)와 `git diff --ignore-cr-at-eol --stat` · 병합 뒤 첫 06:15 실행에서 확인할 것(result.json warnings에 LITE 등록부 줄 없음, POST_APPLY_ALERT_ENGINE_CHECK_FAILED가 남으면 남은 오류 원문) · 남은 위험(CRWD는 분할 기록 전까지 SPLIT_SUSPECTED로 주문표 없음 · M6 10/17 문서에 CRWD 비교 줄이 없는데 코어 ④가 이름 일치로 통과로 읽는 점(auto_core_rules.py 996~1003행) 확인 결과 · 코어가 PLTR·CRWD 매수 주문표를 낼 수 있는 조건 — auto_core_decide.py 1085·1185·1262행 기준, 지금 S7 새 매수 멈춤 중이라 당장 없음).

## 연결표 (analysis-linkage-map-2026-10-05.md 1절 8번)

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| APPROVED_BUY(PLTR·CRWD) | 이 Builder → 사장 PowerShell 병합 | auto_core_tickets.py 61·264행 · auto_core_decide.py 1085행(buy_approved) → 코어 매수 주문표 | 매수 요건 ①③④⑤ 통과 날 PLTR·CRWD 매수 주문표 | 이 테스트 d · 코어 result.json | 연결(병합 뒤) |
| 정책 배수·card_stock_core | 같음 | portfolio_exposure.py 169·1211·1216행 · auto_core_decide.py 1185·1262행(redeploy_ranking) | PLTR·CRWD 보유 때 E 계산에 1배 · 매수 자격 UNREGISTERED 없음 · 실적 금지 구간 판정 대상 · 재배치 순위 후보 | 06:15 노출 검토 unregistered_instrument_held | 연결(병합 뒤) |
| 원본 상품 등록부 8종목 신원 | 같음 | reconcile_broker_state.py 108~122·148행 · validate_registry_consistency.py 38행 | LITE 매일 경고 사라짐 · 새로 산 종목 신원을 대조가 알아봄 | 06:15 코어 result.json warnings | 연결(병합 뒤) — 지금 끊김(11/06~) |
| 통합 점검 134행 승인 목록 | 병합 뒤 이 프로젝트(예약 작업 변경) | integrated-check-prompt-v3.12.x 134행 ② | 통합 점검 행이 '상품 승인 없음' 막힘에서 풀림 | 통합 점검 324행 자기 검사 · 코어와 통합 점검 ② 비교(compare buyReq) | 끊김 — 메울 변경: 규칙 1줄 + H1 + 독립 검토 · 승인 경로: 사장 직접 입력 `예약 작업 변경 승인: 보유·관심 종목 통합 점검` |

## Judge 확인 항목
1. diff가 allowed_files뿐이고(기존 테스트 두 파일은 지정 행만), 권한 표지 줄·주문 경로·schemas 변경이 없다.
2. 등록부 8종목(CRWD 조건 무관)의 법인명·거래소·증권 종류가 보고의 원문 인용(URL·확인 시각)과 맞다. 원문 인용 없이 들어간 종목이 있으면 FAIL.
3. 모든 항목 new_buy_instrument_approved false. watchlist_approved·candidate_status 값이 보고의 소비자 표 이유와 맞고, 새 실행 경로를 열지 않는다(소비자 코드 행 대조).
4. required_canonical_sha256이 실제 등록부의 canonical_hash와 같다(validate_registry_consistency 실행 결과).
5. CRWD 포함 여부가 active-decisions.md의 CRWD 카드 수락 행 유무와 맞다.
6. 정책 문턱(1.9·1.85·1.55·0.4)·add_default·allowed_index_etfs·INDEX_ETFS·PARKING_ETFS 그대로.
7. 대상 테스트 전부 통과, 기준선 실패 외 새 실패 0.
8. 연결표 ③⑤ 원문 행 대조(analysis-linkage-map-2026-10-05.md 1절 8번 · ops-link 규칙: auto_core_tickets.py 61·264행, auto_core_decide.py 1085·1185·1262행, portfolio_exposure.py 169·1211·1216행, reconcile_broker_state.py 108~122·148행, validate_registry_consistency.py 38행, 통합 점검 134·324행). 끊김 행에 메울 변경·승인 경로가 있다.
