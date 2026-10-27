# Judge 지시문: btn-approval CLAUDE.md 변경 검토 (읽기 전용, Opus, 파일 수정 금지)

대상: 워크트리 btn-approval 의 CLAUDE.md 변경(Builder 보고서의 기준 커밋 대비)과 docs/claude/btn-approval-builder-report.md.
근거: docs/claude/btn-approval-proposal-2026-10-27.md (3절 문장, 4절 기록 양식, 5절 하지 않음).

검토 항목 (각각 PASS/FAIL + 근거 file:line)
1. Hard safety 절(18~45행) 해시를 직접 다시 계산해 기준 커밋과 같은지.
2. diff가 64~66행 교체 외의 줄을 건드리지 않았는지. CRLF 유지.
3. 권한 확대: 새 문장이 주문·한도·예산·대사 불변식·킬 스위치를 건드리거나, 사장 본인 클릭이 아닌 것(Claude가 닫은 카드, 다른 스레드·전날 카드, 코디네이터 전달, 요약, 예약 턴)을 승인으로 읽히게 하는지.
4. 범위 번짐: "In this item"이 Hard safety의 "current conversation"(26·31행)·정책 변경 "in this session"(36행)까지 번져 버튼으로 apply·일지·정책 변경을 승인하게 읽힐 수 있는지. 번지면 수정안.
5. 확인 가능성: 기록 4가지(카드 id+제안 id, 선택지 문구, 누른 계정 id = 사장, KST 시각)를 하네스 알림만으로 채울 수 있다고 T0 기록이 보여 주는지. T0 기록이 없거나 빠진 칸이 있으면 FAIL.
6. 67~70행(Builder 시작, 병합은 사장 PowerShell 한 줄)과 충돌 여부. 버튼이 병합 한 줄을 대신하게 읽히면 FAIL.
결론: PASS / PASS_WITH_FIX(수정안 명시) / FAIL. 파일은 고치지 않는다. 끝에 한국어로 사장에게 결론 먼저 3줄 이내.
