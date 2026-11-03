# 독립 검토 지시문: ic-rules-1103 (통합 점검 규칙 v3.12.11 → v3.12.12)

너는 독립 검토자다. 저장소 파일을 고치지 않는다(읽기만). 예외 하나: 판정 보고를 docs/claude/ic-rules-1103-judge-report.md 한 파일에 UTF-8로 쓴다(본 저장소에 못 쓰면 worktree 같은 상대 경로에 쓰고 그 경로를 알린다). 커밋·푸시·병합·예약 작업 변경 안 함. 비밀(.env*, 토큰, 계좌번호)·키움 도구 금지. 보고는 한국어, 결론 먼저, 계좌 금액을 쓰지 않는다.

## 판정 대상
docs/claude/ic-rules-1103-proposal-2026-11-03.md 전체와 그 원문:
- 새 규칙 파일 docs/claude/integrated-check-prompt-v3.12.12-2026-11-03.txt (옛 판 docs/claude/integrated-check-prompt-v3.12.11-2026-11-02.txt)
- 새 지시문 docs/claude/scheduled-prompts/pending-ic-rules-1103/integrated-check-daily.txt (옛 판 docs/claude/scheduled-prompts/integrated-check-daily.txt)
- 줄 비교 pending-ic-rules-1103/rules.diff · loader.diff

## 읽을 원문
- docs/claude/active-decisions.md 31·104·114·115·119·121행과 C절 끝 행(t2-c2-sell), CLAUDE.md(시나리오 🔴 질문 규칙 115행 부근, 승인 규칙 64-78행)
- docs/claude/strategy-revision-2026-11-01.md 4·5절, docs/claude/crash-response-proposal-2026-10-31.md 6·9·10절, docs/claude/market-scenario-27h1-2026-10-09.md 6절 103-106행
- manage-us-stock-strategy/scripts/auto_core_rules.py 238행(ret5)·860-900행(R-REC1 이벤트), 코어 매수 요건 ③ 계산(buy_requirements를 만드는 함수 — grep "카드 표")
- manage-us-stock-strategy/schemas/auto-core-research-record.schema.json(writer)
- docs/claude/redesign-t2-compare-b7-2026-11-03.md, workspace/outputs/auto-core/2026-11-03/decision.json·compare.json
- docs/claude/ic-rules-bundle-proposal-2026-11-02.md(이전 묶음 형식·되돌리기 원본)

## 확인 항목 (각각 PASS/FAIL + 원문 파일·행)
1. 바뀐 곳이 규칙 파일 1·102·124·134·161·170행과 지시문 1·4·12·18·88행뿐이고, 절대 금지·알림 조건·매수 요건 기준·쓰기 범위·대시보드 기록 스키마·기록 전 검증이 그대로인가.
2. 161행 (v)·(vi)이 기록된 사장 결정(10/31 20:24 직접 입력, 11/01 21:34 strategy-1101, 11/01 06:43 SCN-27H1 효력 정지)과 문구·범위가 맞는가. 결정보다 넓게 묻지 않게 만든 곳(예: 결정이 정하지 않은 상황까지 묻지 않음)이 있으면 지적.
3. 161행 (vii)이 CLAUDE.md·active-decisions의 다른 규칙(사장에게 반드시 물어야 하는 것, 카드 수락은 사람 결정 등)과 부딪히는가. kill ①~③ 해당 공식 사실을 놓칠 길이 있는가.
4. 102·124·134행 새 문구가 코어 코드와 같은 뜻인가(EV 세션마다 sigma60[i]·hi20[i], ret5 = close[t]/close[t−5] − 1, ③ "카드 표 N + 새 M" 합산). 다르면 어느 쪽인지 행으로.
5. 170행이 대시보드 calendar·실적 금지 구간 계산 등 다른 규칙과 부딪히는가(예: 금지 구간 시작일이 지난 경우 표시가 필요한가).
6. 해시: 새 규칙 파일 LF 정규화 sha256 = 74440cf5…, 새 지시문 바이트 sha256 = 6c29d74d…, 지시문 18행 값 = 새 규칙 파일 해시. 로더 1단계 python을 원문대로 돌려 MATCH인지(파일을 만들지 않는 heredoc).
7. 이 개정으로 새로 생기는 위험과, 막아야 하면 더 엄격한 조건(더 엄격하게만).

## 출력 형식
첫 줄 `VERDICT: PASS` 또는 `VERDICT: PASS-WITH-CONDITIONS` 또는 `VERDICT: FAIL`. 그다음 항목 1~7 판정과 근거 행, 조건(있으면 번호), 마지막에 읽은 파일 목록.
