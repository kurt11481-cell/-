# Builder 지시문: journal-venue — 결정 일지(S7b)를 사장실 회사PC 스레드가 기록 (수동 경로, K3)

선행 조건(하나라도 없으면 시작하지 않는다. 원본은 본 저장소 E:\사업\##금동한\코덱스저장소\docs\claude\journal-venue-proposal-2026-10-27.md 8·9절이다. 워크트리 사본은 옛 커밋이라 그 절이 없을 수 있다):
① 사장의 착수 승인(사장실 스레드 직접 입력 `journal-venue 착수 승인` 또는 그 스레드 착수 카드 탭, 2026-10-27 이후 같은 날 KST)이 제안서 결정 기록 절에 있음 ② T0(VM에서 `portfolio_review_journal.py verify` 읽기 전용 결과)가 기록되어 있음.
모델: Opus. 작업 위치: 새 워크트리 `journal-venue`(claude --worktree journal-venue). 시작 시 HEAD를 보고서에 적는다(작성 시점 3542b10).

읽을 것: 제안서 2절(현행 원문)·9절(바꿀 것 1~8). CLAUDE.md 전문.

해야 할 일
1. 시작 해시 확인(원본 CRLF 바이트): CLAUDE.md 전체 460ac219b052…40df, Hard safety 18~45행 8ee8d497aa60…f663, 29~34행 f0938237d2b3…81ee, 108행 c5953526e61b…7c84. 다르면 멈추고 보고.
2. manage-us-stock-strategy/scripts/portfolio_review_journal.py: CONFIRMATION_METHODS에 `PROJECT_THREAD_USER_DECISION` 추가. 이 방법에 한해 메시지 속 코드 검사(체인 검사 :181 부근, apply :536 부근)를 면제하고, 대신 user_message가 `<id> | <account id> | <KST 시각> | <원문>` 4칸(빈 칸 없음)인지 검사한다. confirm_code는 제안 코드 그대로. USER_TERMINAL·COWORK 경로와 AUTO_CORE 검사는 바꾸지 않는다. docstring 15~19행에 새 경로 1줄.
3. schemas/portfolio-review-journal.schema.json: confirmation_method enum에 같은 값 추가, description 1문장. 필드는 늘리지 않는다.
4. score_decision_journal.py 등 confirmation_method를 읽는 곳을 찾아(grep) 새 값이 빠지거나 거부되지 않는지 확인하고 보고서에 적는다. 고칠 곳이 있으면 최소 수정.
5. 테스트(test_portfolio_review_journal.py): 새 방법 통과, 4칸 누락·빈 메시지 거부, 기존 방법은 코드 없는 메시지 계속 거부, verify 통과. 대상 테스트 파일만 실행(전체 스위트는 돌리지 않는다).
6. CLAUDE.md: 29~34행에 "사장실 회사PC 스레드(대화형 Claude Code 프로젝트 스레드) 예외 — 그 스레드에서 사장이 직접 친 결정 메시지나 그 스레드가 올린 결정 카드의 사장 탭(64~70행 기록 4가지)이 곧 확인이며, 같은 세션에서 PROJECT_THREAD_USER_DECISION으로 propose→apply→verify" 를 넣고, 108행 "accepted in Cowork"를 "accepted in Cowork or in the 사장실 회사PC 스레드"로. 대조 apply·정책/상태·decision_mode·.claude 문장은 한 글자도 바꾸지 않는다. CRLF 유지(바이트 치환, \n 수 = \r\n 수).
7. .claude/settings*.json은 건드리지 않는다. 주문·한도·예산·주문 단계·승인 상품·대사 불변식·킬 스위치 확대 표현 금지.
8. 보고서 docs/claude/journal-venue-builder-report.md: git diff -U0, 바뀐 파일·줄, 변경 전후 해시(CLAUDE.md 전체, 18~45행 구간은 바뀐 행 번호 포함 새 해시), 테스트 결과, 4번 grep 결과.
9. 커밋·푸시·병합하지 않는다.

끝나면 사장에게 한국어 3줄: 바뀐 파일, 테스트 결과, Judge 시작 방법(docs/claude/journal-venue-judge-prompt.md).
