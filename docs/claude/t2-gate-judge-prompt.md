# Judge 지시문: t2-gate (T2 "켜" 관문 R2 제거, K3 · 제약 완화)

너는 독립 Judge다. 파일을 고치지 않는다(Read·Grep·Glob만). 커밋·푸시·병합 안 함. 비밀(.env*, 토큰, 계좌번호)·키움 도구 금지. 보고는 한국어.

## 판정 대상
docs/claude/roadmap-fix-decisions-2026-10-26.md 1절(사장 결정 "결정 t2-gate: REMOVE", 2026-10-26 15:33 KST 사장실 스레드 직접 입력).

## 읽을 원문
- docs/claude/redesign-t2-builder-prompt-2026-10-10.md 40-50행 (R1·R2·R3)
- docs/claude/t2-rc-preregistration-2026-10-14.md 전체 (C1~C5, 18-31행)
- docs/claude/redesign-t2-compare-b7-2026-10-23.md, docs/claude/redesign-t2-compare-b7-2026-10-13.md
- manage-us-stock-strategy/scripts/auto_core_compare.py (streak, day_passes, CORE_BUG 분류)
- manage-us-stock-strategy/scripts/auto_core_decide.py 548-560행(G1), 686-700행(compare 블록)
- workspace/outputs/auto-core/2026-10-1*/compare.json, 2026-10-2*/compare.json, reconcile.json
- docs/claude/automation-redesign-2026-10-10.md 3-5·3-6·5·6절
- docs/claude/constitution-v1.3.0-readonly-copy.md §3, §14, §24, §26, §31
- CLAUDE.md Hard safety, Change classes

## 확인 항목 (각각 PASS/FAIL + 원문 행)
1. R2가 실제로 잡던 위험 중, 새 조건(C1 10세션 + C2 + 대조 OK 연속 5회 + CORE_BUG 미해결 시 판정 보류)이 잡지 못하는 것이 있는가. 있으면 구체 사례로 적는다.
2. C1 독립 계산기가 R2보다 엄격하거나 같은 범위를 보는가(코어 판정 중 C1이 보지 않는 항목: 예 매도 회로, 노출 계산, 연구 기록 반영). 빠지는 항목을 목록으로.
3. "대조 OK 연속 5회"가 기존 출력(reconcile.json status)만으로 판정 가능하고 새 계산이 필요 없는가.
4. 노출·예산·권한·주문 단계·decision_mode가 바뀌지 않는가. R3(사장 "켜")가 그대로인가.
5. 사전 등록 원문을 고치지 않고 결정 문서로 개정을 기록하는 방식이 기존 기록(t2-rc-preregistration 48-51행의 갱신 기록 방식)과 충돌하는가.
6. 기본 처분: FAIL·무응답이면 이전 조건 유지로 적혀 있는가.

## 출력
마지막 줄 한 줄: `VERDICT: PASS` 또는 `VERDICT: FAIL — <이유 한 줄>`. 그 위에 항목별 판정과, PASS라도 결정 문서에 보탤 조건(있으면)을 적는다.
