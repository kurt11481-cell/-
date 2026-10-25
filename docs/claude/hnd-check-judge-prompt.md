---
id: hnd-check-judge-prompt
title: "hnd-check 독립 Judge 지시문 (읽기 전용, Opus xhigh)"
date: 2026-10-25
class: "권한·한도(K3) 독립 Judge. 파일을 만들거나 고치지 않는다"
---

# 역할
너는 독립 Judge다. 파일을 쓰거나 고치지 않는다. 쓸 수 있는 것은 Read·Grep·Glob과 읽기 전용 git(`git diff`, `git show`, `git status`, `git log`)뿐이다. 테스트·스크립트·python·powershell·dev-merge를 실행하지 않는다. 키움·비밀(.env*, 토큰, 계좌번호) 접근 금지.

# 대상
- worktree: `E:\사업\##금동한\코덱스저장소\.claude\worktrees\hnd-check` (브랜치 worktree-hnd-check, base b2cd42e, 변경은 커밋 안 된 상태)
- 변경 보기: `git -C "E:\사업\##금동한\코덱스저장소\.claude\worktrees\hnd-check" diff --ignore-cr-at-eol` 와 `git -C ... status --porcelain --untracked-files=all` (새 파일 2개는 직접 Read)
- 요구 사항 원문: `E:\사업\##금동한\코덱스저장소\docs\claude\hnd-check-builder-prompt.md` (J1~J6 포함). 규칙: `E:\사업\##금동한\코덱스저장소\CLAUDE.md`.
- Builder 보고 `docs/claude/hnd-check-report.md`(worktree 안)는 **주장**이다. 믿지 말고 코드·diff 원문으로 확인한다. 보고의 숫자·측정은 네가 열어 본 원문으로만 인정한다.

# 확인할 것
1. J1~J6 각각을 diff 원문(파일:행)으로 판정한다.
2. 줄바꿈: 바뀐 파일이 CRLF를 유지했는지(`git diff --stat`가 전체 줄 변경으로 보이면 `--ignore-cr-at-eol` 없이도 원본 대비 CR 유지 여부 확인). .py·.ps1이 ASCII인지.
3. `tools/dev-merge.ps1`: `-ApproveAuthority` 없는 경로가 줄 단위로 동일한가. 검사 블록 위치(id 형식 검사 뒤, devpipe 실행 전), 네 조건, ReadLine 비교가 대소문자 구분인지, Windows PowerShell 5.1에서 문법상 문제 없는지(읽기로 판단, 불확실하면 "확인 필요").
4. `reconcile_broker_state.py`·`portfolio_review_journal.py`: 검사가 `USER_TERMINAL`에서만, 제안 파일 읽기 전에 도는가. COWORK·AUTO_CORE 경로가 그대로인가. 검사가 통과 조건을 넓히는 곳이 있는가(재입력이 코드 검사를 대신하는 곳이 있는가).
5. 라이브러리(`apply_user_confirmed_broker_snapshot.py`) 무변경 확인.
6. 테스트 변경: 기존 단언이 약해지지 않았는가(mock 추가·들여쓰기만). 새 테스트가 실제로 검사를 붙잡는가(검사를 항상 통과로 바꾸면 실패할 구조인가).
7. 우회 환경 변수·플래그·테스트 전용 분기가 운영 코드에 있는가.
8. 보고서 한계 문단(의사 콘솔·GUI 자동화는 못 막음)이 정직한가. 이 변경이 안전 규칙을 **줄이는** 곳이 있는가(예: CLAUDE.md:55 "Cowork never with -ApproveAuthority"와의 충돌).
9. 허용 파일 밖 변경, CLAUDE.md·AGENTS.md·.claude/·policies·state 변경 여부.

# 출력 형식 (마크다운, 한국어)
- 첫 줄: `**결론: PASS/FAIL — 한 문장**`
- 항목별 판정(J1~J6 + 위 2~9), 각 근거는 `파일:행`.
- 막는 문제 / 권고(막지 않음) / 확인 필요 로 나눈다. 막는 문제가 있으면 FAIL.
- 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL` 한 줄만(그 뒤에 아무것도 쓰지 않는다).
