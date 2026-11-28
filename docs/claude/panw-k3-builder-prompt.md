---
id: panw-k3-builder-prompt
title: "PANW 신규 매수 상품 승인 — 수동 경로 Builder 지시문"
date: 2026-11-28
status: "초안 — 착수 전. 수동 경로(정책·등록부는 개발 큐 보호 경로, 선례 swing-k3·qqq-reg)"
class: "authority(K3). Builder Opus(worktree panw-k3) → 별도 읽기 전용 Judge(Opus) → 병합은 사장 PowerShell 병합 스크립트 docs/claude/panw-k3-merge-<날짜>.ps1"
allowed_files: "workspace/policies/instrument_registry.json · stock-strategy-system/alert_policy.json · manage-us-stock-strategy/scripts/auto_core_tickets.py · manage-us-stock-strategy/tests/test_panw_k3_registration.py(새로) · manage-us-stock-strategy/tests/test_swing_k3_registration.py(83·107행 기대값과 148·149행 대조 기호만) · manage-us-stock-strategy/tests/test_portfolio_exposure.py(105~107·112행 기대값만) · docs/claude/panw-k3-report.md"
source: "사장 직접 입력 2026-11-28 15:17:27 KST — docs/claude/panw-k3-proposal-2026-11-28.md · 선례 docs/claude/swing-k3-builder-prompt.md(형식·지킬 것 그대로)"
card_condition: "PANW 관심 카드 v1 수락 2026-11-28 15:08:45 KST(active-decisions.md cyber-lead-1128-accept 행). 착수 때 그 행과 card-evidence-registry.json PANW 항목이 있는지만 다시 확인 — 기준 커밋(2026-11-28 23:30 문서 커밋 이후)에서, 없으면 메인 작업 트리 절대 경로에서"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 상태·일지·원장·예약 쓰기 없음"
weekly_user_touch: "1 (병합: 사장 PowerShell 1번)"
---

## 목표
PANW를 신규 매수 승인 상품에 넣는다(코드 목록·정책 배수·카드 핵심), 원본 상품 등록부 PANW 신원을 공식 출처로 검증해 적는다.

## 바꿀 내용

### A. workspace/policies/instrument_registry.json — PANW 항목만
- CRWD 항목과 같은 필드로: legal_issuer_name · instrument_type "stock" · security_class · exchange · trading_currency "USD" · identity_status "verified_primary_source" · identity_verification_status "VERIFIED" · official_identity_source_url · official_identity_source_type "SEC_10_K" · identity_verified_at(KST) · leverage_factor 1.0 · leverage_factor_status "verified".
- 신원 출처: SEC 10-K(2026-09-10 제출) https://www.sec.gov/Archives/edgar/data/1327567/000132756726000023/panw-20260731.htm 표지(법인명·증권 종류·거래소 원문). 열지 못하면 멈추고 docs/claude/panw-k3-BLOCKED.md(가정 금지).
- new_buy_instrument_approved false · short_sale_approved false · confirmation_proxy null 유지. watchlist_approved·candidate_status·portfolio_bucket은 swing-k3 보고(docs/claude/swing-k3-report.md)의 소비자 표와 CRWD에 고른 값의 이유를 다시 확인해 같은 기준으로(새 실행 경로를 여는 값이면 닫힌 쪽). theme·subtheme 그대로.
- registry_version은 바꾸지 않는다(swing-k3-BLOCKED.md 2번 — 픽스처 decision-record.valid.test-only.json 7행이 고정). 다른 항목·키·순서·들여쓰기 무변경.
- stock-strategy-system/alert_policy.json decision_harness.instrument_registry_authority.required_canonical_sha256을 validate_registry_consistency의 canonical_hash로 다시 계산(이 키만). 정책 사본 decision_harness.instrument_registry는 건드리지 않음.

### B. stock-strategy-system/alert_policy.json — portfolio_exposure_policy
- nominal_multipliers에 "PANW": 1을 "QQQ": 1 앞에(형식 유지). card_stock_core 끝에 "PANW".
- 그 밖(add_default card_add_stock_only·allowed_index_etfs·문턱·single_stock_*·묶음 A 3배 상한 키) 무변경.

### C. manage-us-stock-strategy/scripts/auto_core_tickets.py
- 61행 APPROVED_BUY 끝에 "PANW", 60행 주석 끝에 "; PANW: user approval 2026-11-28 panw-k3-1128". ASCII만.

### D. 새 테스트 manage-us-stock-strategy/tests/test_panw_k3_registration.py
  a. 실제 등록부: PANW identity_status "verified"로 시작, 모든 항목 new_buy_instrument_approved false.
  b. 실제 두 파일로 validate_registry_consistency 해시 오류 없음.
  c. 실제 alert_policy: PANW 배수 1·card_stock_core 마지막이 PANW·앞 9종목 순서 그대로, 문턱 1.9·1.85·1.55·0.4·add_default card_add_stock_only 그대로.
  d. APPROVED_BUY = 기존 12개 + PANW, INDEX_ETFS·PARKING_ETFS 그대로.
  e. canonical_identity_errors({"PANW"}, 실제 등록부) == [].
  f. 실적 기록이 없으면 PANW 증가가 EARNINGS_DATE_UNVERIFIED로 막힘(test_swing_k3의 같은 시험 방식). 대조: 승인 밖 개별주(예 "NOW"·"NTSK")는 APPROVED_BUY에 없음.

## 테스트
- 기존 테스트는 값을 통째로 고정한 줄만: test_swing_k3_registration.py 83행(card_stock_core == 앞 7 + PLTR·CRWD → 앞 9가 그 값)·107행(APPROVED_BUY == 앞 10 + PLTR·CRWD → 앞 12가 그 값)·148·149행(대조 기호 PANW → 승인 밖·미검증인 다른 기호, 등록부 원문으로 고름), test_portfolio_exposure.py 105~107·112행. 그 밖에 바뀌어야 통과하는 테스트가 있으면 멈추고 BLOCKED에 적는다.
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"` — 패턴 test_panw_k3_registration.py · test_swing_k3_registration.py · test_portfolio_exposure*.py · test_qqq_registration.py · test_policy_a.py · test_auto_core*.py · test_reconcile_broker_state.py · test_validate_decision_record.py · test_v2_2_tactical_radar.py · test_instrument_identity_authority.py · test_portfolio_decision_order_intent.py, 그리고 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`. 기준선 실패는 고치지 않고 이름만 보고.

## 지켜야 할 것 (어기면 Judge FAIL)
swing-k3-builder-prompt.md '지켜야 할 것' 1~5와 같다: auto_core.py·reconcile apply·키움·run_auto_core.ps1 실행 금지 · 권한 표지 줄·주문 경로 문자열·schemas 무변경 · allowed_files만, 줄바꿈 유지(git i/lf·작업 트리 CRLF), scripts ASCII · 통합 점검 규칙·예약 지시문 무변경 · git commit·push·병합 없음(worktree에 커밋하지 않은 채).

## 보고 docs/claude/panw-k3-report.md
바뀐 줄(파일:행, 앞뒤 값) · PANW 신원 원문 인용(URL·확인 시각) · 필드 값과 이유 · 테스트 결과(Ran 수·실패 0)와 `git diff --ignore-cr-at-eol --stat` · 바뀐 파일 sha256 표 · 병합 뒤 첫 06:15·07:45 실행에서 볼 것 · 남은 위험(R-REC1, PANW 종가 이력 없음, NTSK·NET이 M6 글자 일치로 ④ 통과로 읽히는 점).

## Judge 확인 항목
1. diff가 allowed_files뿐(기존 테스트 두 파일은 지정 행만), registry_version 무변경, 권한 표지·주문 경로·schemas 무변경.
2. PANW 법인명·거래소·증권 종류가 보고의 SEC 원문 인용과 맞다.
3. 모든 항목 new_buy_instrument_approved false, PANW 다른 필드 값이 이유와 맞고 새 경로를 열지 않는다.
4. required_canonical_sha256 == 실제 등록부 canonical_hash.
5. 카드 수락 행(cyber-lead-1128-accept)과 card-evidence-registry PANW 항목이 있다(기준 커밋 또는 메인 작업 트리).
6. 정책 문턱·add_default·allowed_index_etfs·INDEX_ETFS·PARKING_ETFS 그대로, 다른 종목 배수·순서 그대로.
7. 대상 테스트 통과, 기준선 밖 새 실패 0.
8. 연결표(수정안 5절) ③⑤ 원문 행 대조, 끊김 행에 메울 변경·승인 경로가 있다.
마지막 비지 않은 줄은 `VERDICT: PASS` 또는 `VERDICT: FAIL`.
