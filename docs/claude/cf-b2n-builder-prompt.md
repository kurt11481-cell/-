---
id: cf-b2n-builder-prompt
title: "외부 유출(출금·환전)을 브로커 잔액 두 조회 일치로 인정 — 대조 I3 예외 B2-N (관제판 cashflow-api-gap)"
date: 2026-10-25
class: "권한·한도(K3) — 대조 불변 조건 3이 받아들이는 현금 증거. 수동 경로: worktree Builder → 별도 읽기 전용 Judge(Opus) → 병합은 사장 결정"
source: "사장 \"결정 cashflow-proof: B2-N\"(2026-10-23 09:25 KST) + \"결정 cashflow-proof 착수: 승인\"(2026-10-25 08:12 KST, 투자_V2 비서실 — 직접 입력). 검토 docs/claude/cashflow-proof-options-2026-10-23.md 7·8절(재검토 2회)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 주문 도구 없음 · 정책·상태 파일 쓰기 없음(정책 변경이 필요하면 보고만)"
weekly_user_touch: "0 (병합 결정 1번)"
---

## 목표
키움에는 출금·환전 **거래 기록** 조회가 없고 거래내역(ust21100)에도 출금이 안 나온다. 그래서 2026-10-22 출금 −82.93이 대조 I3 `CASH_CHANGE_NOT_EXPLAINED`로 영구 HOLD를 만든다(recon-dt 병합 5a289b8 뒤에도 남는 유일한 사유). 아주 좁은 조건에서만, 브로커 잔액 두 조회가 같은 유출 금액을 가리키면 I3를 통과시키되 **출금을 손실로 남긴다(HWM 조정 0)**. 그 밖은 지금처럼 HOLD.

## 사실 (2026-10-23 조회, 진단 문서 원문)
- ust21132 "특정일 통화별 예수금 및 증권 평가금"(kiwoomcli `overseas accounts cash-by-currency-date --date YYYYMMDD`) result_list USD `fx_entr`: 10/19 12,469.19 · 10/20 82.94 · 10/21 150.02 · 10/22 150.04, `won_entr` 모두 0. base_dt = **미국 거래일**, 미정산 매수를 거래일에 미리 뺀 값(≈ 스냅숏 주문가능액 fc_ord_alowa와 0.01~0.03 차이), 주말은 직전 영업일 값 유지, 당일 값은 장 마감 뒤 생성(그 전에는 "내역 없음").
- 10/21 미국 거래일 체결 순현금(수수료 포함) = 매도 15,392.30 − 매수 15,242.27 = +150.03. 10/20→10/22 원장 변화 +67.10 → L = 67.10 − 150.03 = −82.93. 스냅숏 잔차 R(recon-dt 뒤 재생) = −82.93.

## 바꿀 내용
1. **조회 추가(읽기 전용):** `manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py` ACCOUNT_APIS에 ust21132(`/api/us/acnt`)를 날짜 지정 읽기로 추가하고, 자동 코어의 날짜 읽기 경로(run_auto의 reader·plan)에서 **I3가 유출 후보일 때만** 필요한 base_dt 2개를 읽는다. **I1 필수 조회에는 넣지 않는다**(조회 실패는 이 예외 분기에서만 HOLD). 키움 읽기 정책 파일(workspace/policies/kiwoom-readonly-policy.json 등)의 허용 대상에 추가가 필요하면 **정책 파일을 고치지 말고**(권한상 거절됨) 필요한 정확한 변경(JSON 경로·값)을 보고에 적는다 — 병합 때 사장 승인으로 Cowork가 반영한다. 이 경우 테스트는 정책 허용이 없을 때 HOLD가 나는지도 보인다.
2. **I3 예외 분기(auto_core_reconcile.py explain_change, 지금 `CASH_CHANGE_NOT_EXPLAINED`를 붙이는 곳 근처):** 아래를 **모두** 만족할 때만 `CASH_CHANGE_NOT_EXPLAINED` 대신 I3를 통과시키고, I3 결과에 `unverified_outflow_usd`(양수 금액)·`unverified_outflow_basis`(두 base_dt, fx_entr 두 값, 거래일 체결 순현금, L, R)를 남기며, 결과 warnings에 `UNVERIFIED_EXTERNAL_OUTFLOW:<금액>`을 1줄 넣는다.
   a. R < −CASH_TOLERANCE_USD(유출). 유입(R > +허용)은 이 분기로 절대 인정하지 않는다.
   b. 다른 I3 사유가 하나도 없다(FILL_AMOUNT_UNAVAILABLE·정산 불일치·SETTLEMENT_D0 계열·UNCLASSIFIED 등이 있으면 이 분기에 들어가지 않는다). I1·I2·I4·I5는 그대로 판정된다.
   c. base_before = 기준 기록(마지막 OK 기록) 시점까지 끝난 마지막 미국 거래일, base_after = 이번 스냅숏 시점까지 끝난 마지막 미국 거래일(운영 달력 사용). 두 날 모두 ust21132 USD fx_entr가 return_code 0으로 있고 "내역 없음"이 아니다. 아니면 HOLD(`UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE`).
   d. 그 사이 모든 체결의 session_date(recon-dt 뒤 = 미국 주문일)가 (base_before, base_after] 안이다. 밖이면 HOLD(`UNVERIFIED_OUTFLOW_SPAN_MISMATCH`).
   e. L = fx_entr(base_after) − fx_entr(base_before) − Σ(그 구간 미국 거래일별 체결 순현금, 수수료 포함; 이미 쓰는 ust21610 당일매매 금액) − Σ(그 구간 ust21100 분류 흐름). |R − L| ≤ 0.05이고 L < −CASH_TOLERANCE_USD. 아니면 HOLD(`UNVERIFIED_OUTFLOW_NOT_MATCHED:<R>:<L>`).
   f. 유출 금액 ≤ 기준 기록의 주문가능액. 아니면 HOLD.
   g. 원화 예수금(won_entr)이 두 base_dt 사이에 늘었으면(환전 유입 의심) HOLD.
3. **바꾸지 않는 것:** `cash_flow_evidence.py`(신고 블록·상태·SETTLED_STATUSES·hwm_adjustment) — 새 신고 상태를 만들지 않는다. 신고는 지금처럼 NO_EXTERNAL_FLOW로 남아 **HWM 조정 0**이 저절로 성립한다(portfolio_exposure.py 지분식). I1·I2·I4·I5 판정식, CASH_TOLERANCE_USD, FILL_WINDOW_MAXIMUM_DAYS, plan_reads 범위, 정산 규칙, 주문·한도·관문.
4. **문서:** `docs/claude/automation-redesign-2026-10-10.md` 3-5 불변 조건 3(111행) 끝에 한 문장 추가: "예외 — 거래내역에 없는 외부 유출은, 유출이고 다른 I3 사유가 없으며 브로커 스냅숏 잔차와 ust21132 미국 거래일 예수금 원장 잔차가 $0.05 안에서 같을 때만 인정하고 미확인 외부 유출로 표시하며 HWM은 조정하지 않는다(사장 결정 cashflow-proof B2-N, 2026-10-23/25)." `manage-us-stock-strategy/references/broker-snapshot-reconciliation.md`의 I3 설명에도 같은 내용.

## 테스트 (새 파일 manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py, 기존 테스트 파일 무변경, 키움·네트워크 없음 — 리더 주입)
- 10-23 재현: R −82.93, ust21132 10/20 82.94·10/22 150.04, 10/21 체결 순현금 +150.03 → I3 PASS, unverified_outflow_usd 82.93, warnings에 UNVERIFIED_EXTERNAL_OUTFLOW:82.93, cash_flow_evidence 신고 NO_EXTERNAL_FLOW·hwm_adjustment 0(또는 None — 기존 그대로) 확인.
- 유입(R +50, L +50) → HOLD. R·L 차이 0.06 → HOLD. ust21132 조회 실패·"내역 없음" → HOLD. 체결 session_date가 구간 밖 → HOLD. 다른 I3 사유(FILL_AMOUNT_UNAVAILABLE) 동반 → 예외 미적용·HOLD. 유출 금액 > 기준 주문가능액 → HOLD. won_entr 증가 → HOLD. 정책 허용 없음(구현상 해당되면) → HOLD.
- 기존 동작: 잔차 |R| ≤ 1이면 ust21132를 읽지 않는다(리더 호출 0 확인).

## 검토 순서 (보고에 한 줄씩)
NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD.

## 지켜야 할 것 (어기면 Judge FAIL)
1. `auto_core.py`·`reconcile_broker_state.py apply`·작업 등록 스크립트·`kiwoomcli`를 실행하지 않는다. 예약 작업 변경 없음. 키움 호출 없음. 상태·정책·일지·원장 파일 쓰기 없음.
2. `cash_flow_evidence.py`, I1·I2·I4·I5, 허용 범위, 조회 창, 정산 규칙을 바꾸지 않는다. 유입을 인정하는 코드를 넣지 않는다. HWM을 조정하는 코드를 넣지 않는다.
3. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY` 줄 변경 없음. 매도를 막는 조건 추가 없음. 한도·관문 변경 없음.
4. 판단이 안 되면 HOLD(fail-closed). 새 조회는 I1 필수 목록에 넣지 않는다.
5. 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`와 전체 스위트로, 시작 전 기준선(실패·오류 **이름 목록을 파일 없이 보고에 그대로 적는다**)과 끝난 뒤를 비교해 새 실패 0. "auto_core.py"가 든 명령 금지.
6. 허용 파일만: manage-us-stock-strategy/scripts/auto_core_reconcile.py, manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py, (필요할 때만) 자동 코어의 날짜 읽기 요청을 만드는 파일 1개(보고에 이유), manage-us-stock-strategy/schemas/의 대조 결과 스키마(새 필드가 스키마 검사에 걸릴 때만), manage-us-stock-strategy/references/broker-snapshot-reconciliation.md, docs/claude/automation-redesign-2026-10-10.md(111행 한 문장만), manage-us-stock-strategy/tests/test_auto_core_reconcile_outflow.py, docs/claude/cf-b2n-report.md. CRLF 등 각 파일 기존 줄바꿈 유지.
7. git commit·push·병합·강제·브랜치 삭제 없음. 변경은 worktree에 커밋하지 않은 채로 둔다(병합 때 Cowork가 커밋).

## 보고 docs/claude/cf-b2n-report.md
바뀐 줄(파일:행), 규칙 요약, 정책 파일 변경 필요 여부와 정확한 변경안, 테스트 결과(기준선·이후 실패/오류 **이름 목록**), 남은 위험. 반드시 포함: (a) 두 조회는 같은 잔액을 다른 TR로 읽는 것이라 출금 "증명"이 아니라 기록 허용까지만 (b) HWM 조정 0 — 출금이 손실로 남음 (c) 유입(입금·이자)은 여전히 HOLD (d) 06:15 시점에 직전 미국 거래일 ust21132 값이 있는지는 첫 실행에서 확인 필요 — 없으면 HOLD (e) recon-dt2(주문표 주문일 창) 미해결.

## Judge 확인 항목
1. diff가 I3 예외 분기, ust21132 읽기 추가(I1 밖), 결과 필드·경고, 문서 두 곳뿐이다. cash_flow_evidence·I1/I2/I4/I5·허용 범위·조회 창·정산 무변경.
2. 예외는 2a~2g를 모두 만족할 때만 적용되고, 하나라도 어긋나면 HOLD다(테스트가 각 조건을 보인다). 유입은 절대 인정 안 됨.
3. HWM 조정이 생기지 않는다(신고 블록 그대로, 테스트로 확인).
4. 잔차가 허용 안이면 새 조회를 하지 않는다.
5. 주문·권한 줄 변경 없음, 매도 차단 추가 없음, 허용 파일만, 줄바꿈 유지, 기준선 대비 새 실패 0(이름 비교), 보고 (a)~(e)와 정책 변경안(필요 시).
