---
id: tax-pretax-note-2026-10-25
type: note
title: "주문표·현행 점수는 세전 (D12)"
as_of: "2026-10-25 KST, 기준 커밋 bb11f04"
class: "사실 연결 노트. 새 규칙·정책·코드 변경 없음"
authority: "order_authority=false · quantity_authority=none"
source_decision: "사장 D12 a 승인(2026-10-25 08:46Z, d6-builder-prompt.md) · 근거 operating-diagnosis-2026-10-25.md 9-3"
consumers: "세후 결과를 내려는 검토·카드·M6 세션(세후 숫자를 쓰기 전 확인) · redesign-t4 SYSTEM.md 첫 판"
---

# 세전 기준과 세후 결과의 조건

자동 코어의 주문표와 지금의 점수(일지 채점 `score_decision_journal.py`의 주문표 vs 아무것도 안 함, 카드 결정 vs SPY)는 **세전** 값이다. 근거: 주문표 계산·판정·채점 코드(`auto_core_tickets.py`·`auto_core_decide.py`·`auto_core_rules.py`·`score_decision_journal.py`)에 세금 항목이 없다. `auto_core*.py`·`score_decision_journal.py`에서 "tax"가 나오는 곳은 대조기 `auto_core_reconcile.py`(12·91·635행)뿐이고, 그것은 브로커 기록의 현금 흐름 종류(배당·수수료·세금)를 나누는 일이다(이 세션의 grep). 세후 결과는 스킬 references가 이미 정한 대로 **승인된 세금 가정이 있을 때만** 낸다. `manage-us-stock-strategy/references/portfolio-policy.md` 99행 "Include expense ratios, commissions, spread, slippage, dividend tax, capital-gains assumptions, FX conversion, and turnover." 100행 "State Korean-resident and account-type assumptions before presenting after-tax KRW results." `manage-us-stock-strategy/references/capital-redeployment.md` 34-35행 "If cost, slippage, and tax assumptions are not approved, show gross proceeds and `ASSUMPTION_REQUIRED`." 지금 승인된 세금 가정은 찾지 못했으므로(docs/claude 밖 .json·.py에서 "tax assumption"·"tax_assumption"·"after-tax" 0건, 이 세션의 grep) 세후 숫자는 `ASSUMPTION_REQUIRED`로 표시하고 세전 값만 보인다. 세율·기본공제 수치(외부 글 검토 문서 external-triangle-support-strategy-review-2026-10-13.md:89의 22%·연 250만 원)는 공식 출처로 확인하지 않았다 → **확인 필요**. 이 노트는 새 규칙이 아니고, 매매 근거·예산·한도·권한에 영향이 없다.

검토 완결: 원문 확인 5/5(portfolio-policy.md 99-100행, capital-redeployment.md 34-35행, auto_core*.py·score_decision_journal.py grep, 세금 가정 grep, external-triangle…:89) · 내장 재검토 0회(사실 연결, 결정 요청 없음) · 미해결 1(세율·공제 공식 수치) · 자료 시점 2026-10-25 KST · 바뀔 조건: 세금 가정이 승인되거나 코드에 세금 계산이 들어오면 고친다.
