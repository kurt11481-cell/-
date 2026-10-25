---
id: hnd-check2-judge-prompt
title: "hnd-check2 독립 Judge 지시문 (읽기 전용)"
date: 2026-10-25
class: "권한·한도(K3) 독립 Judge. 파일을 만들거나 고치지 않는다"
---

# 역할
독립 Judge다. 파일을 쓰거나 고치지 않는다. 쓸 수 있는 것은 Read·Grep·Glob과 읽기 전용 git(`git diff`, `git show`, `git status`, `git log`)뿐이다. 테스트·python·powershell·dev-merge를 실행하지 않는다. 키움·비밀(.env*, 토큰, 계좌번호) 접근 금지.

# 대상
- worktree: `E:\사업\##금동한\코덱스저장소\.claude\worktrees\hnd-check2` (브랜치 worktree-hnd-check2, base b6a83e2, 변경은 커밋 안 된 상태). 변경 보기: `git -C "<worktree>" diff --ignore-cr-at-eol`, `git -C "<worktree>" status --porcelain --untracked-files=all`(새 파일은 직접 Read).
- 요구 사항: `E:\사업\##금동한\코덱스저장소\docs\claude\hnd-check2-builder-prompt.md` 와 `hnd-check2-fix1-prompt.md`(J1~J8). 앞 변경: `hnd-check-report.md`, `hnd-check-judge-report.md`(병합 b6a83e2). 규칙: 메인의 `CLAUDE.md`(최근 d124 병합으로 승인 장소·터미널 경로 문구가 바뀌었다. 이번 변경이 그 문구와 충돌하는지 본다).
- Builder 보고 `docs/claude/hnd-check2-report.md`(worktree 안)는 **주장**이다. 코드·diff 원문으로 확인한다.

# 확인할 것
1. 허용 파일 밖 변경, CLAUDE.md·AGENTS.md·.claude/·policies·state 변경, 라이브러리 `apply_user_confirmed_broker_snapshot.py` 변경 여부.
2. 재입력 제거가 완전한가(id·코드 비교 흔적, `STOP_ID_NOT_CONFIRMED`, `USER_TERMINAL_CODE_NOT_RETYPED` 잔재). 지운 만큼 쓰이지 않는 로케일 키·상수만 지웠는가.
3. **통과 조건 확대 0**: dev-merge.ps1과 Python 두 CLI에서, 새 순서(기존 네 조건 → GetConsoleMode 두 핸들 → Enter 한 번)가 거절만 더하는가. NUL·파이프·파일 리다이렉트·입력 끝이 각각 어디서 막히는지 `파일:행`으로 따라간다. Enter 단계가 내용을 비교하지 않는데 이것이 통과 집합을 넓히는 곳이 있는가.
4. PowerShell 5.1: `Add-Type`/P/Invoke 코드의 문법·핸들 상수(-10/-11), 예외 시 fail closed, ASCII 전용 소스, Enter 블록 위치(devpipe 실행 전), `$null` 처리.
5. Python: Windows 아닐 때의 동작(테스트 환경), GetConsoleMode ctypes 사용(타입·핸들 처리), `input()` 1회, EOFError 거절, KeyboardInterrupt 비포획, COWORK·AUTO_CORE 경로 불변.
6. 테스트: 제거·변경된 시험 목록이 보고와 일치하는가, 단언 약화·skip 추가가 없는가, 새 시험이 실제로 붙잡는 구조인가. 줄바꿈 CRLF 유지, .py·.ps1 ASCII.
7. 우회 환경 변수·스위치·테스트 전용 분기가 운영 코드에 없는가.
8. 보고서 한계 문단이 정직한가(숨은 새 콘솔·의사 콘솔·키 입력 주입은 못 막고 Enter를 기다리며 멈추는 점). CLAUDE.md의 d124 문구(승인 장소·"Cowork는 -ApproveAuthority를 붙이지 않음" 등)와 이번 README·reference 문구가 충돌하지 않는가.
9. 보고서의 측정 주장(NUL, 숨은 콘솔 15초 대기, Ctrl+C "확인 필요")은 근거를 읽을 수 있는 범위에서만 인정하고, 못 읽는 것은 "확인 필요"로 둔다. 테스트 결과는 실행 권한이 없어 확인할 수 없으면 확인 필요로 적는다.

# 출력 형식 (마크다운, 한국어)
- 첫 줄: `**결론: PASS/FAIL — 한 문장**`
- 항목별 판정(근거 `파일:행`), 막는 문제 / 권고(막지 않음) / 확인 필요.
- 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL` 한 줄만.
