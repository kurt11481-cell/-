# Judge 지시문: t2-c2-sell (T2 "켜" 조건 C2를 매도 주문표로도 인정, K3 · 제약 완화 H2)

너는 독립 Judge다. 저장소 파일을 고치지 않는다(읽기만). 예외 하나: 판정 보고를 docs/claude/t2-c2-sell-judge-report.md 한 파일에 UTF-8로 쓴다. 커밋·푸시·병합 안 함. 비밀(.env*, 토큰, 계좌번호)·키움 도구 금지. 보고는 한국어, 결론 먼저.

## 판정 대상
docs/claude/t2-c2-sell-proposal-2026-11-03.md 전체(사장 결정 카드 2026-11-03 19:42:26 KST "매도 주문표로도 검증 인정").

## 읽을 원문
- docs/claude/t2-rc-preregistration-2026-10-14.md 전체(0절 고정 규칙, 1절 C1·C2, 2절 C3·C4, 끝 변경 기록)
- docs/claude/t2rc-oracle.py — ticket_check(2007행 부근), c2_item_match(1605·1651행 부근), 매도 수량 계산(재배치 다리)
- docs/claude/scheduled-prompts/auto-core-alert.txt 와 docs/claude/scheduled-prompts/auto-core-alert/core.py — "주문표 확인 대기" 문구가 나오는 조건(C3·M3)
- docs/claude/roadmap-fix-decisions-2026-10-26.md 1-1~1-3절, docs/claude/active-decisions.md btn-approval 행·t2-gate 행
- manage-us-stock-strategy/scripts/auto_core_tickets.py 58행 부근(POLICY_EXPECTED)
- workspace/outputs/auto-core/2026-10-27 ~ 2026-11-03 폴더의 decision.json(buy_requirements·tickets·blocked)·t2rc-check.json

## 확인 항목 (각각 PASS/FAIL + 원문 파일·행)
1. 바뀌는 것이 사전 등록 C2 한 줄뿐이고, R1·C1·C3·C5·차이 분류 의무·CORE_BUG 보류·대조 OK 5회·R3 사장 "켜"가 그대로인가.
2. 계산기 ticket_check가 매도 주문표를 매수와 같은 깊이(수량 정수, LOC 가격 센트, 관문, should_exist)로 다시 계산하는가. 매도에서만 빠지는 항목이 있으면 적는다. c2_item_match가 방향과 무관한가.
3. C3·M3가 실제로 동작하는가: 켠 뒤 방향별 첫 주문표가 계산기 일치 기록 전이면 알림이 "주문표 확인 대기 — 입력 금지"를 보내는지 알림 지시문·core.py에서 확인. 매수 첫 주문표가 이 경로를 빠져나갈 길이 있으면 사례로.
4. 제안서 2절의 사실(10-27~11-03 매수 요건 ②·⑤ 전부 막힘, 11-03 SOXL sell 후보와 G1 막힘, target_exposure 1.55)이 원문과 맞는가.
5. 사장 승인 기록이 btn-approval 조건(카드·제안 id, 선택지, 누른 계정=사장, KST 시각)을 채우는가. 이 카드가 decision_mode '켜'까지 승인하는 것으로 읽힐 문구가 없는가.
6. 이 완화로 새로 생기는 위험(예: 켠 뒤 첫 매수 결함, 매도 주문표만 검증된 상태의 매도 단계 G3 결함)을 더 엄격한 조건으로 막아야 하면 조건을 제시하라(더 엄격하게만).

## 출력 형식
첫 줄 `VERDICT: PASS` 또는 `VERDICT: PASS-WITH-CONDITIONS` 또는 `VERDICT: FAIL`. 그다음 항목 1~6 판정과 근거 행, 조건(있으면 번호), 마지막에 읽은 파일 목록.
