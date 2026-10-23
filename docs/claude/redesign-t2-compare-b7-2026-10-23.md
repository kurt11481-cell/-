---
id: redesign-t2-compare-b7-2026-10-23
title: "T2 비교 모드 미설명 차이(B7) 설명 기록 — 10-20·10-21·10-22"
date: "2026-10-23"
status: "기록 5건(LLM_ERROR) · 미설명 유지 10건 · 코드 수정 필요 0"
authority: "표시·기록 전용 · 주문·정책·상태·관문 무관"
consumers: "auto_core_compare.py R2 연속 일수(다음 decide) · 관제판 redesign-t2 · '켜' 판정 세션"
source: "workspace/outputs/auto-core/2026-10-20·21·22/compare.json·decision.json·s7 · research-records/2026-10-20·21·22 · 규칙 파일 v3.12.8(10-20)·v3.12.9(10-21·22)"
---

## 결론
- redesign-t2-compare-explained.json에 **LLM_ERROR 5건** 추가(13 → 18건, load_explained 오류 0): 10-20 buyReq:DELL:1 · 10-21 buyReq:LITE:3·buyReq:PWR:3 · 10-22 buyReq:SOXL:3·R5:SOXL.
- R2 하루 통과(auto_core_compare.py 313~318행 day_passes): 10-20 탈락 · **10-21 통과** · 10-22 탈락 → 다음 decide 기준 연속 일수 0(필요 5) — 지금과 같음.
- 10-21 decide는 07:58 중단 뒤 10:45 KST 재실행되어 비교가 있었다(generated_at 2026-10-21T01:45:58Z).

## 미설명으로 둔 것 (10건)
- **10-20 R5 묶음 5건**(buyReq:NBIS:2·buyReq:SOXL:2·R5:MVLL·R5:NBIS·R5:SOXL): 그날 규칙 v3.12.8 101행은 상태형(종가 ≤ 0.70×P면 검토 개시)이라 LLM이 문구대로 했고, 코어는 S7 사건형. 같은 날 사장 결정 r5-align: 1로 규칙을 코어 정의에 맞춤(v3.12.9, 코드 변경 0, 10-21부터 B1). LLM_ERROR도 아니고, 사장이 코어 정의를 채택했으므로 CORE_BUG로 적는 것도 사실과 맞지 않아 미설명으로 둔다(연속 일수 결과는 어느 쪽이든 같음 — 10-20은 DELL 외 항목 때문에 어차피 탈락).
- **10-22 NBIS 트리거 4건 + exposure:N**: 입력 시각 차이 — 코어 06:15 브로커 스냅숏(NBIS 13 보유) vs LLM 06:4x 잔고(NBIS 없음, BE 28). 각자 자기 입력에 규칙대로 적용. 대조 모듈의 시각 차이(B6) 판정 범위를 넓히는 것은 사전 등록 부록 B의 사후 변경이라 NO_CHANGE.

## 코드 수정이 필요한 것
- 없음. 개선 후보(권한 경로, 지금 안 함): 트리거 대조가 LLM 실행에 없는 종목을 "LLM 미충족"으로 셈(auto_core_compare.py 197~211행, 매수 요건 행은 219~221행에서 건너뜀).

## 바뀔 조건
- 10-22 06:15~06:4x 체결이 시간외 거래가 아니라고 확인되면 NBIS·N 5건 재판정.
- **확인됨(2026-10-23 06:44 KST, 사장 원문 "06:15~06:4x 체결은 시간외 거래임")** → 입력 시각 차이 판정 유지, NBIS 4건·exposure:N 미설명 유지 확정. 미해결 0.

검토 완결: 원문 확인 — B7 목록 3일(compare.json)·day_passes 313~318행·DELL earnings·SOXL + 쪽 hit(C2+만)·LLM SOXL ③ 문구·peakReviews[0].state·LITE/PWR 카드 23행·v3.12.8 133행은 비서실이 직접 확인, 나머지 수치는 하위 에이전트 보고(재계산 근거 파일 명시) · 내장 재검토 0회(변경·결정 요청 없음 — L 점검만) · 미해결 0(10-22 시각 차이는 사장 확인 06:44) · 자료 시점 decide 10-20 07:45, 10-21 10:45, 10-22 07:45 KST.
