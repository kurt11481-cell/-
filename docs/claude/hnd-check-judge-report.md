---
id: hnd-check-judge-report
title: "hnd-check 독립 Judge 보고 (읽기 전용, Opus, Read·Grep·Glob·읽기 전용 git)"
date: "2026-10-25"
verdict: "PASS (막는 문제 0, 권고 4, 확인 필요 3)"
source: "docs/claude/hnd-check-judge-raw.md (claude -p 출력). 그 파일은 PowerShell 파이프가 한글을 CP949로 잘못 해석해 글자가 깨졌다. 이 보고는 깨진 원문에서 읽히는 내용만 옮긴 것이며, 판정·근거 위치·마지막 줄은 원문 그대로다."
---

## 결론
허용 파일 안에서 USER_TERMINAL apply와 `-ApproveAuthority` 병합을 "거절만 더하는" 대화형 콘솔 검사가 들어갔다. 일반 병합·COWORK·AUTO_CORE 경로와 라이브러리는 바뀌지 않았고 막는 문제는 없다. (비교 방법: 이 Judge 세션에서 git diff 본문 출력이 거부되어, 메인 체크아웃(HEAD b2cd42e)과 worktree를 `git diff --no-index --stat`과 직접 Read로 비교했다.)

## 항목별 판정
- **J1 / 9 허용 파일 밖 변경 없음 — PASS.** 바뀐 것은 dev-merge.ps1(+21), README.md, 로케일 json, reference 문서, journal.py, reconcile.py, 기존 테스트 4개(mock 추가·들여쓰기만), 새 테스트 test_approval_human_check.py. CLAUDE.md, AGENTS.md, .gitignore, .claude 설정·agents, workspace/policies, stock-strategy-system, workspace 변경 0. docs는 hnd-check-report.md 하나만 새로 생김. BLOCKED.md 없음. 로케일 파일은 `reconcile_broker_state.py:42`의 LOCALE_PATH가 가리키는 메시지 목록 파일.
- **J2 / 불변 경로 — PASS.** dev-merge.ps1은 기존 줄이 순서까지 같고 추가는 4행 주석과 38~56행 `if ($ApproveAuthority)` 블록뿐. reconcile 새 분기는 `reconcile_broker_state.py:286`의 `== "USER_TERMINAL"` 안에만, journal은 `portfolio_review_journal.py:826-829`에만. append_auto_core_entries 무변경. `apply_user_confirmed_broker_snapshot.py` 무변경.
- **J3 / 통과 조건 확대·우회 없음 — PASS.** 두 CLI 실패는 모두 반환 2로 끝나고(`reconcile_broker_state.py:290-294`, `portfolio_review_journal.py:827-829`), 통과하면 기존 흐름이 처음부터 그대로다. 재입력은 코드 검사를 대신하지 않는다(`test_approval_human_check.py:152-156`). 운영 코드에 우회 환경 변수·플래그·테스트 분기 없음(dev-merge의 `$env:`는 기존 ComSpec·SystemRoot뿐, param은 Id·ApproveAuthority뿐: `dev-merge.ps1:19-22`, 고정 시험 `test_dev_pipeline.py:1319`).
- **J4 / 비대화형 실제로 막힘 — PASS(코드 경로 확인).** dev-merge 검사(`dev-merge.ps1:42-46`)는 id 형식 검사 뒤, devpipe 실행(58행 이후) 앞. 네 조건(IsInputRedirected, IsOutputRedirected, Host.Name, UserInteractive) 모두 있고 id 비교는 `-cne`(대소문자 구분, 52행), EOF($null)는 불일치로 중단. Python은 `isatty() is True` 둘 다 요구, 스트림 없음은 비대화형, NUL처럼 isatty가 참이어도 읽을 것이 없으면 EOFError로 거절. 두 CLI 모두 제안 파일 읽기 전에 검사(reconcile 286 < 295, journal 826 < 830).
- **J5 / 단언 약화 없음 — PASS.** 기존 테스트는 patch 추가와 `with` 들여쓰기만 바뀌었고 단언은 그대로. 새 테스트는 검사를 붙잡는 구조(`test_both_streams_must_be_a_terminal`, `test_terminal_apply_without_a_console_is_refused`, `test_authority_switch_without_a_console_stops` 등). 새 파일 테스트 수 16 = 4+7+5.
- **J6 / 한계 정직·안전 규칙 축소 없음 — PASS.** 보고서 18행에 GUI 자동화는 못 막는다는 한계가 원문 그대로 있고, ConPTY·콘솔 입력 주입도 못 막는다고 적었으며 Desktop Commander가 파이프인지는 "확인 필요"로 남겼다. README 11·70행 문구는 CLAUDE.md:55("never with -ApproveAuthority")·61과 충돌하지 않는다.
- **줄바꿈·ASCII — PASS.** 바뀐 12개 파일 모두 `[^\r]$` 일치 0건(CRLF 유지). dev-merge.ps1·reconcile.py·journal.py 비ASCII 0건(안내문 한글은 `\u` 이스케이프, `dev-merge.ps1:48-50`).
- **PS 5.1 문법 — PASS(읽기 판단).** 괄호 안 `-or` 줄바꿈, `''` 이스케이프, `[Console]::IsInputRedirected` 모두 5.1에서 문제 없음.
- **CLI import 위치 — PASS.** USER_TERMINAL 분기 안에서만 지연 import, 순환 없음. import 실패는 삼켜지지 않아 apply 없이 오류로 끝남(fail closed).

## 막는 문제
- 없음.

## 권고 (막지 않음)
1. Builder 보고 107행의 "이전 dc-dev Q2 a에서는 Cowork가 병합할 수 있었다" 문장은 CLAUDE.md:55가 Cowork의 `-ApproveAuthority` 사용을 이미 금지하므로 부정확하다. 문구를 고치면 좋다.
2. `docs/claude/dc-dev-2026-10-22.md:38`의 "Cowork가 `-ApproveAuthority`로 병합" 문구는 Cowork가 문서를 갱신할 후보다(이 세션에서 열지 않음).
3. journal 재입력 안내가 영어다(`portfolio_review_journal.py:71`, scripts ASCII 규칙 때문). 다음 일반 변경에서 로케일 키로 옮길 수 있다.
4. 수동 경로 병합 스크립트(`docs/claude/<id>-merge-*.ps1`)는 README:44 문서 규칙으로만 덮이고 코드로 강제되지 않는다.

## 확인 필요
1. 테스트 결과: Builder 보고의 "기준선 대비 새 실패 0(PLTR 1건)"은 Builder의 주장이다. Judge는 실행 권한이 없어 확인하지 못했다. 병합 뒤 아래 테스트를 다시 돌려 확인해야 한다: test_approval_human_check*, test_reconcile_broker_state*, test_portfolio_review_journal*, test_decision_journal_cards*, test_dev_pipeline*, test_auto_core*.
2. Desktop Commander 셸이 파이프인지 의사 콘솔(ConPTY)인지. 의사 콘솔이면 이 검사를 통과하고, 그 경우 방어는 절차 규칙만 남는다.
3. 대화형 성공 경로의 실제 동작(PS 5.1 창에서 프롬프트를 띄우고 ReadLine으로 받는 경로)은 자동 시험이 안 된다. 보고서의 사람 시험 절차(원문 글자 깨짐으로 정확한 행은 확인 필요, 대략 112행 이후)로 확인해야 한다.

VERDICT: PASS
