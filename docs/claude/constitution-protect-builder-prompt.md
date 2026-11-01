# Builder 지시문: constitution-protect (수동 경로, K3 — tools/ 보호 경로)

모델: Opus. 작업 위치: 새 워크트리 `constitution-protect`(claude --worktree constitution-protect, 또는 `git worktree add .claude/worktrees/constitution-protect -b worktree-constitution-protect HEAD`). 시작 HEAD를 보고에 적는다(작성 시점 6b0a248, 브랜치 codex/master-recovery-expansion).

선행 조건(원본: docs/claude/top-guideline-review-2026-11-01.md 10절):
- 사장 직접 입력 "헌법 보호 1줄 진행" · cmsg_0137MRzn9nuDvvQmVxm6WeX9DkqHb9dy5YezxV2rM8XzGT · user_01KuMGKfZu1SBYxtMmg4vAiH · 2026-11-01 11:12:31 KST.
- 바로 앞 제안: 같은 스레드 cmsg_0137MRzn9nuDvvQmVxm6WeX9R49dxxPXr8kJKE4z7zLpwG — "헌법 파일이 보호 목록(authority-paths.txt)에 없어 개발 큐 작업이 고쳐도 사장 승인 단계에서 멈추지 않는다. 1줄 추가를 권한다."

할 일(이것만):
1. tools/dev_pipeline/authority-paths.txt(ASCII, CRLF, 65행, 끝 \r\n)의 끝에 아래 3행을 CRLF로 덧붙인다. 기존 65행은 바이트 그대로 둔다.
   - 빈 행
   - `# Fund constitution, top document (user decision 2026-11-01; docs/claude/top-guideline-review-2026-11-01.md sections 10-11)`
   - `docs/claude/constitution-v*.md`
2. 대상 테스트만 돌린다(전체 테스트 금지, 바이트코드 금지). 워크트리 루트에서:
   `python -B -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py" -k authority_paths`
   마지막 3줄을 보고에 적는다.
3. 확인해 보고에 적는다: `git status --porcelain --untracked-files=all` 결과가 tools/dev_pipeline/authority-paths.txt 한 줄뿐인지, 그 파일의 변경 전·후 sha256(원본 바이트), 줄 수(65 → 68), CR 수 = LF 수, ASCII 여부.
4. 커밋·푸시·병합하지 않는다. .claude/settings*.json·CLAUDE.md·AGENTS.md·정책·상태 파일은 손대지 않는다. 주문·키움 도구는 쓰지 않는다.

보고: 한국어로 회신한다(파일로 쓰지 않는다 — 사장실 스레드가 docs/claude/constitution-protect-builder-report.md로 옮긴다). 시작 HEAD, 워크트리 경로·브랜치, 변경 전·후 sha256, `git diff` 전문, 테스트 결과, status 결과. 막히면 우회하지 말고 멈춰서 이유를 적는다.
