# 재확인 지시문: ic-rules-1103 수정본 (바뀐 줄만)

너는 독립 검토자다. 저장소 파일을 고치지 않는다(읽기만). 예외 하나: 판정 보고를 docs/claude/ic-rules-1103-recheck-report.md 한 파일에 UTF-8로 쓴다(본 저장소에 못 쓰면 worktree 같은 상대 경로에 쓰고 그 경로를 알린다). 커밋·푸시·병합·예약 작업 변경 안 함. 비밀(.env*, 토큰, 계좌번호)·키움 도구 금지. 보고는 한국어, 결론 먼저, 계좌 금액을 쓰지 않는다.

## 배경
첫 독립 검토(docs/claude/ic-rules-1103-judge-report.md)가 PASS-WITH-CONDITIONS로 조건 1~6을 냈다. 작성자가 조건 1~5를 반영한 수정본을 만들었다. 이번에는 그 반영이 맞는지만 본다(나머지 줄은 첫 검토에서 PASS).

## 판정 대상
- 규칙 파일 docs/claude/integrated-check-prompt-v3.12.12-2026-11-03.txt (옛 판 docs/claude/integrated-check-prompt-v3.12.11-2026-11-02.txt)
- 지시문 docs/claude/scheduled-prompts/pending-ic-rules-1103/integrated-check-daily.txt (옛 판 docs/claude/scheduled-prompts/integrated-check-daily.txt)
- docs/claude/ic-rules-1103-proposal-2026-11-03.md 2·3·7·10절

## 확인 항목 (각각 PASS/FAIL + 원문 행)
1. 옛 판과 diff: 규칙 파일은 1·102·124·134·161·170행만, 지시문은 1·4·12·18·88행만 바뀌었는가.
2. 조건 1: 161행 (vii) 예외가 강 후보(−) 공식 사실 전부·알림 ① 보유 매도 근거 새 충족·미해제 RG1 공식 테제 훼손을 결정 필요에 남기고, 0줄 문구가 "kill 미해당"이 아닌가. 보유 카드의 − 강 후보(규칙 파일 116·124·130·131·332행)가 "등 … 전부"로 빠짐없이 덮이는가.
3. 조건 2: 161행 (v)가 노출 E 수준과 이미 이탈한 선 아래 머무는 것만 덮고, V6·S7 검토선(L1~L4) 가운데 직전 기록보다 더 깊은 선을 처음 이탈한 날은 결정 필요에 올리는가. "E·총자산이 새 구간에 들어가는 것만으로는" 문구가 없는가. 직전 기록을 못 읽은 날 어느 쪽으로 처리되는지 적고, 더 엄격하게 해야 하면 조건으로.
4. 조건 3: (a) 끝 "이미 정한 일" 줄이 E ≥ 1.9 / 1.55 ≤ E < 1.9 / E < 1.55 / E 모름(확인 필요) 네 경우로 갈리고, active-decisions.md 114·119행 결정 문구와 맞는가.
5. 조건 4: 134행 ③에 "같은 종류는 한 번만 센다"가 있고 코어 auto_core_tickets.py 127·147행(종류 집합·basis_met)과 같은 뜻인가.
6. 조건 5: 170행이 끝나지 않은 금지 구간을 "진행 중(~끝 날짜)"으로 남기고, 지난 일 판정을 일정 끝 날짜 기준으로 하며, (e) 금지 구간 달력(172행)에도 같게 적용되는가.
7. 해시: 규칙 파일 LF 정규화 sha256 = 76d0fb533a1bdec27d7f9b0fdd924cdb1a3529ef05ae232ea3b0cb8e1d6cc855, 지시문 바이트 sha256 = 5b9238564d9dd46648d391f1b6459af42985d62b96afb2c71d6480a8de34baef, 지시문 18행 값 = 규칙 파일 해시. 지시문 1단계 python을 원문대로(경로만 이 PC 경로로) 돌려 MATCH인지(파일을 만들지 않는 heredoc).
8. 이번 수정 문구로 새로 생기는 위험(더 엄격하게만 조건).

## 출력 형식
첫 줄 `VERDICT: PASS` 또는 `VERDICT: PASS-WITH-CONDITIONS` 또는 `VERDICT: FAIL`. 그다음 항목 1~8 판정과 근거 행, 조건(있으면 번호), 마지막에 읽은 파일 목록.
