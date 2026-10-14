---
id: c3-state-decision-2026-10-14
title: 상태형 C3 해석 결정 기록 (c3-state)
date: 2026-10-14
decision: 사용자 "결정 c3-state: a" (2026-10-14 15:27 KST, Cowork 대화)
class: 결정 기록(문서). 코드·규칙 파일·정책·상태 변경 없음
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: manage-us-stock-strategy/scripts/auto_core_compare.py(설명 파일) · docs/claude/redesign-t2-day2-check-2026-10-14.md 4절 · 관제판
---

# 상태형 C3 해석 결정 (c3-state)

## 1. 결정
- a = 상태형 C3±는 처음 성립(규칙 파일 107행: 2회 연속 마감, 그 앞 종가는 반대쪽) 뒤 종가가 EMA20의 같은 쪽에 있는 동안 "유지 중" 1개로 센다(113행). 코어 현행(auto_core_rules.py 318~325행)과 같다. 코드 변경 없음.
- 규칙 파일 v3.12.4(현행, 2026-10-14 10:28 적용) 107·113행 문구는 v3.12.2와 같다(Cowork diff 확인).

## 2. 결과
- 대조: LLM이 "유지 중"을 빠뜨리면 LLM_ERROR. 2026-10-14 MVLL:trend_recover를 redesign-t2-compare-explained.json에 기록(MVLL은 09-15 EMA20 아래 뒤 09-16~10-13 20세션 연속 위).
- 2026-10-14는 MU 2건 CORE_BUG가 있어 연속 일수에 들지 않는다(auto_core_compare.py day_passes).
- 매수 쪽: 유지 중 C3+는 약한 단서 1종(auto_core_tickets.py 120행). 새 근거(new_kinds)는 첫날만. S7 추가 대상 종목은 basis_met만으로 회로가 열린다(722행). MVLL은 매수 불가 상품(표시만).
- 매도 쪽: 유지 중 C3-도 매도 근거로 남는다(709행 basis_met).

## 3. 남은 일(미해결, 기본 처분 NO_CHANGE)
- 113행 문구 보완: 사용자 "c3-rule: 1"(2026-10-14 15:40) → v3.12.5 초안 완료(integrated-check-v3.12.5-change-2026-10-14.md), 10/15 07:35 R2 교체와 함께 적용 예정(승인 1회). 적용 전 10/15 실행분 차이는 Cowork가 설명해야 한다.
- 대조 분류: DELL·PWR trend_recover 10-14는 B2(가격 여유 2.86%·2.70%, 3% 이내)로 분류됐지만 원인은 가격 여유가 아니라 해석 차이다(b2_wide 대상). 분류 규칙 수정은 일반 변경(dev 파이프라인).

## 4. 줄바꿈 "수정됨" 표시 재검토(같은 세션)
- 사용자 PC의 Linux 셸 git은 core.autocrlf 설정이 없어 i/lf·w/crlf 파일을 수정됨으로 본다(auto_core_rules.py와 테스트 4개).
- `git -c core.autocrlf=true status`로는 이 파일들이 깨끗하고, docs/claude/c6-fix-review-2026-10-14.md만 내용이 바뀌었다.
- 2026-10-14 08:37 Windows 실행 result.json guarded_dirty_paths = [] (auto_core.py 등도 i/lf·w/crlf인데 잡히지 않음) → Windows git은 줄바꿈을 정규화한다. 앞선 "apply 모드에서 F6로 멈춤" 판단은 철회.
- 확정 증거: 다음 06:15 daily의 guarded_dirty_paths(커밋 1a2b7d6 뒤 첫 Windows 실행).
