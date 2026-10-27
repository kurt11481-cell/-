# Judge 지시문: journal-venue (읽기 전용, Opus · xhigh, K3)

파일을 고치지 않는다. 워크트리 journal-venue의 변경을 본 저장소 기준(HEAD 3542b10)과 비교해 판정한다.
읽을 것: docs/claude/journal-venue-proposal-2026-10-27.md 2·8·9절, journal-venue-builder-report.md, git diff.

판정 항목(각 PASS / PASS_WITH_FIX / FAIL + 근거 파일:행)
1. 범위: 바뀐 파일이 CLAUDE.md·portfolio_review_journal.py·journal 스키마·해당 테스트·(필요 시) 채점기 최소 수정·보고서뿐인가. .claude/** 변경 없음.
2. Hard safety 번짐: 대조 apply·정책/상태·decision_mode·주문·권한 문장이 바뀌지 않았는가. 새 예외가 결정 일지 S7b에만, 사장실 회사PC 스레드에만 걸리는가.
3. 승인 증명: 새 방법이 하네스 기록 4가지 없이 통과할 수 있는 길이 있는가(빈 칸, 구분자 위조, 다른 방법 이름 재사용). Claude가 닫은 카드·코디네이터 인용이 인정될 여지가 문장에 남았는가.
4. 기존 경로 불변: COWORK_CHAT_USER_MESSAGE·USER_TERMINAL의 코드 검사, AUTO_CORE null 검사, 해시 체인, 1시간 만료가 그대로인가. 테스트가 이를 확인하는가.
5. 소비자: score_decision_journal.py 등 confirmation_method를 읽는 코드가 새 값을 정상 처리하는가.
6. CRLF·해시: 보고서의 전후 해시를 다시 계산해 일치하는가.

결과를 docs/claude/journal-venue-judge-report.md에 쓰지 말고(읽기 전용) 사장에게 한국어로 판정 표와 수정안만 전달한다. 기록은 사장실 스레드가 옮긴다.
