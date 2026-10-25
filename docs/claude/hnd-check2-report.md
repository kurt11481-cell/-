---
id: hnd-check2-report
title: "hnd-check2 Builder 보고 — id/코드 재입력 제거, '진짜 콘솔 핸들' 검사(GetConsoleMode)로 대체 + 수정 1(Enter 한 번)"
date: 2026-10-25
class: "권한·한도(K3) 후속, 수동 경로 Builder. worktree hnd-check2(브랜치 worktree-hnd-check2, base b6a83e2). 커밋·병합 없음"
source: "docs/claude/hnd-check2-builder-prompt.md, 수정 1은 docs/claude/hnd-check2-fix1-prompt.md (둘 다 메인 체크아웃의 미커밋 파일로 읽음 — 이 worktree에는 없다)"
authority: "order_authority=false · quantity_authority 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음 · CLAUDE.md·AGENTS.md·.claude/ 무변경"
consumers: "독립 Judge(J1~J8) · 사장(병합 결정, 대화형 시험) · Cowork(남은 위험 1의 판단 재료, 남은 위험 4의 문서 갱신)"
---

# 수정 1 — Enter 한 번 (2026-10-25, docs/claude/hnd-check2-fix1-prompt.md)
이 절이 최신이다. 아래 "결론"부터는 앞 Builder 기록이며, 수정 1로 바뀐 곳에는 "수정 1 이후" 문장을 덧붙였다(지운 문장 없음, 사람 시험 절차만 새 동작에 맞게 고쳐 씀).

## 요약
- 재입력(문자열 비교)은 **되살리지 않았다.** 모든 콘솔 검사를 통과한 **뒤에** Enter 한 번을 기다린다. 입력 내용은 비교하지 않는다(빈 줄이든 아무 글자든 줄이 오면 진행). 입력 끝·오류는 기존 거절과 같다: dev-merge `DEV-MERGE <id> STOP_NOT_INTERACTIVE` exit 2, reconcile `apply_terminal_not_interactive`·반환 2, journal `기록하지 않았습니다: USER_TERMINAL_NOT_INTERACTIVE`·반환 2. 새 종료 코드·새 STOP 이름·우회 스위치·환경 변수 없음. `--confirm` 코드 일치 검사(라이브러리) 그대로. COWORK·AUTO_CORE·일반 병합 경로 불변.
- **숨은 새 콘솔 측정**(이 PC, `Start-Process -WindowStyle Hidden`, 15초): 수정 전 복사본은 1.9초 만에 모든 검사를 통과해 가짜 devpipe를 `merge … --id hnd-selftest --approve-authority`로 불렀고, Python 검사도 즉시 통과(None)했다. 수정 후에는 둘 다 15초 동안 끝나지 않았고(강제 종료), 숨은 창 화면 버퍼에는 안내문과 바로 뒤의 커서만 있었다. 가짜 devpipe 호출 0, 로그 폴더 0.
- 테스트: 기준선(수정 1 전) 대비 **새 실패 0**(알려진 PLTR 1건만). 지운 시험 0, 새 시험 5개, 바꾼 시험 9개(아래).

## 바뀐 줄 (수정 1, 변경 후 기준)
| 파일 | 행 | 내용 |
|---|---|---|
| tools/dev-merge.ps1 | 4-5 | Usage 머리 주석에 "then waits for Enter once." |
| 〃 | 40-42 | 검사 주석의 한계 문구: "a new console window, a pseudo console or automation … still passes" → "a pseudo console, or automation typing into a real or a new console window (which waits at the Enter step below), still passes" |
| 〃 | 74-87 | **신규 Enter 단계**(GetConsoleMode 검사 뒤, `if ($ApproveAuthority)` 블록의 마지막, python 찾기·로그 폴더·devpipe 전): 주석 3줄, `$entered = $null`, `try { Write-Host -NoNewline 'Authority merge. Press Enter to continue (Ctrl+C cancels): '; $entered = [Console]::ReadLine() } catch { $entered = $null }`, `if ($null -eq $entered) { … STOP_NOT_INTERACTIVE; exit 2 }`. ASCII 안내로 충분해 유니코드 이스케이프는 쓰지 않았다 |
| manage-us-stock-strategy/scripts/portfolio_review_journal.py | 17-19 | 모듈 설명 apply 줄: "…no pipe or NUL, then Enter pressed once" (줄 나눔만 바뀜) |
| 〃 | 71-72 | 신규 상수 `TERMINAL_ENTER_PROMPT = "Press Enter to apply (Ctrl+C cancels): "` |
| 〃 | 838-844 | `user_terminal_rejection` 설명: Enter 한 번, 내용 비교 없음, 입력 끝 거절, 새 콘솔은 여기서 기다림, 한계 문구 |
| 〃 | 852-855 | **신규**: `try: input(TERMINAL_ENTER_PROMPT)` / `except EOFError: return TERMINAL_NOT_INTERACTIVE` (isatty·GetConsoleMode 통과 뒤, 함수의 `return None` 바로 앞. 공용 함수에 넣어 두 CLI가 함께 씀 — REUSE) |
| manage-us-stock-strategy/scripts/reconcile_broker_state.py | 8-10 | 모듈 설명 apply 줄만. 실행 코드 무변경: 입력 끝 거절은 기존 `if user_terminal_rejection() is not None:` → `apply_terminal_not_interactive`·반환 2로 간다 |
| manage-us-stock-strategy/assets/locales/reconcile-broker-state-ko-KR.json | 52 | `apply_terminal_not_interactive` 문구(키 무변경): "직접 실행하고 Enter를 한 번 눌러야 합니다", "…헤드리스 셸이거나, Enter 없이 입력이 끝났습니다" — 입력 끝도 이 문구로 나오므로 사실에 맞게 |
| manage-us-stock-strategy/references/broker-snapshot-reconciliation.md | 180-187 | 3절 Fallback 문단: "press Enter once when asked", 내용 비교 없음·입력 끝 거절, 제안 파일 읽기 전, 한계 문장(아래 "한계"와 같은 뜻) |
| tools/dev_pipeline/README.md | 11, 44, 70 | 11: "직접 실행하고, 안내가 나오면 Enter를 한 번 누른다" + "수정 1: 그 검사를 모두 통과한 뒤 Enter 한 번 — 입력 내용은 비교하지 않고, 입력 끝·오류면 같은 STOP_NOT_INTERACTIVE". 44: 수동 경로 병합 스크립트 규칙에 "그 뒤 Enter 한 번(ReadLine이 `$null`이거나 예외면 중단, 내용 비교 없음)". 70: "직접 실행하고 Enter 한 번" |
| manage-us-stock-strategy/tests/test_approval_human_check.py | 1-7, 41, 129-182, 302-309, 328-357, 410-421, 440-458 | 아래 시험 목록 |
| manage-us-stock-strategy/tests/test_dev_pipeline.py | 1299, 1308-1318, 1324-1328, 1571, 1608-1633 | 아래 시험 목록 |
| docs/claude/hnd-check2-report.md | 이 절 + "수정 1 이후" 문장들 | 이 보고 |

CRLF 유지(바뀐 9개 파일 모두 bare LF 0), `.py`·`.ps1` 비ASCII 0(측정). `apply_user_confirmed_broker_snapshot.py` sha256 6884b197e2f059c0… 그대로(HEAD와 diff 없음). 허용 목록 밖 변경 0.

## 시험 (수정 1) — 지운 시험 0, skip 추가 0
### 바꾼 시험
| 이전 | 이후 | 바뀐 단언 |
|---|---|---|
| TerminalCheckTests.test_a_console_goes_on_without_reading_anything | test_a_console_goes_on_after_one_enter_whatever_is_typed | "stdin 0바이트·출력 없음" → 빈 줄·코드·다른 코드·아무 글·두 줄 모두 통과, **정확히 한 줄만** 읽음(`tell`), 출력 = 안내문 한 번. 안내문 글자 고정. 입력 끝(`""`) 경우는 새 시험으로 옮김(거절로 바뀜) |
| TerminalCheckTests.test_no_bypass_input_in_the_check | (같은 이름) | 금지어 `input(`을 두 함수 모두에서 → 핸들 검사에서는 그대로 금지, `user_terminal_rejection`에서는 **정확히 1회**, `input(TERMINAL_ENTER_PROMPT)`가 단독 줄(결과를 담지 않음), `= input(` 없음, 핸들 검사 뒤에 위치. 나머지 금지어·인자 없음 단언 그대로 |
| ReconcileApplyTests.test_refused_before_the_proposal_is_read | (같은 이름) | 경우 추가: 콘솔·핸들 통과 + Enter 대신 입력 끝 → 같은 거절. 비교를 `strip()`에서 출력 전체 일치로(더 엄격) |
| ReconcileApplyTests.test_the_console_check_never_replaces_the_code_check | (같은 이름) | Enter(빈 줄)와 "Enter 자리에 맞는 코드를 쳐도" 두 경우로 — 둘 다 `CONFIRM_CODE_MISMATCH`, 무변경 |
| ReconcileApplyTests.test_console_apply_goes_on_without_typing_the_code | test_console_apply_goes_on_after_one_enter | "input()이 불리면 실패" → `input`이 안내문으로 정확히 1번 불림(`wraps`), 출력 = 안내문 + 적용 성공 문구. revision 8·원장(USER_TERMINAL, 코드)·핸들 1회 단언 그대로 |
| JournalApplyTests.test_an_existing_journal_stays_byte_identical | (같은 이름) | 경우 추가: 입력 끝 → 거절, 바이트 동일 |
| JournalApplyTests.test_console_apply_records_without_typing_the_code | test_console_apply_records_after_one_enter | "input()이 불리면 실패" → 아무 글 + Enter로 기록, `input` 1번, 출력이 안내문으로 시작, 항목의 `confirm_code`는 `--confirm` 코드, 친 글은 일지에 없음 |
| StaticScriptTests.test_merge_authority_needs_an_interactive_console | (같은 이름) | 지운 단언: "`ReadLine`·`Write-Host`가 파일에 없음"(수정 1이 넣는 것). 더한 단언: Enter 블록 전체 글자 일치, GetConsoleMode 판정 뒤·블록의 마지막, STOP_NOT_INTERACTIVE 2 → 3, `ReadLine` 1회·`Write-Host` 1회·`$entered` 4회(비교에 쓰일 자리 없음), `-cne`·`-ceq` 없음. 그대로: `Read-Host`·`STOP_ID_NOT_CONFIRMED`·`Unescape` 없음, 위치, param, `$env:`, test·bypass·skip 없음 |
| MergeCopyConsoleTests.test_authority_switch_without_a_console_stops | (같은 이름) | 경우 추가: 에이전트가 파이프로 Enter(`\r\n`)를 넣어도 STOP_NOT_INTERACTIVE, devpipe 0 |

### 새 시험 5개
| 시험 | 무엇을 |
|---|---|
| TerminalCheckTests.test_the_end_of_input_is_refused | 숨은 새 콘솔 흉내: isatty 참·핸들 참인데 입력이 끝남(빈 stdin, `input`이 EOFError) → `USER_TERMINAL_NOT_INTERACTIVE`, 안내문 1번 |
| TerminalCheckTests.test_ctrl_c_at_the_enter_step_is_left_alone | `KeyboardInterrupt`는 잡지 않고 그대로 올라간다 |
| ReconcileApplyTests.test_console_apply_without_an_enter_is_refused | CLI 끝까지: 입력 끝 → 반환 2, 출력 = 안내문 + `apply_terminal_not_interactive`, 상태·감사 파일 무변경 |
| JournalApplyTests.test_console_apply_without_an_enter_is_refused | CLI 끝까지: 입력 끝 → 반환 2, 출력 = 안내문 + `기록하지 않았습니다: USER_TERMINAL_NOT_INTERACTIVE`, 일지 안 생김 |
| MergeCopyConsoleTests.test_enter_step_goes_on_for_any_line_and_stops_at_the_end_of_input | 다른 복사본 시험은 모두 콘솔 검사에서 멈춰 Enter 단계에 닿지 않으므로, 복사본의 Enter 블록을 글자 그대로 떼어 Windows PowerShell에서 실행: 빈 줄·아무 글·두 줄 → 진행(첫 줄만, 내용 그대로), NUL·빈 파이프 → `STOP_NOT_INTERACTIVE` exit 2, NUL/NUL → exit 2 |

- 그대로 통과(단언 무변경): NUL·파이프·파일 거절 시험 전부(`RealHandleTests` 2, 두 CLI의 NUL 끝-끝 2, 복사본 NUL 1, C# 블록 1), 비대화형 거절, 핸들 실패 거절, COWORK 경로 2개, 일반 병합 회귀.
- 숨은 새 콘솔 자체를 띄우는 시험은 스위트에 넣지 않았다: 창을 띄우고 몇 초 기다린 뒤 죽여야 해서 느리고, 데스크톱이 없는 예약 작업 실행 환경에서 흔들릴 수 있다. 대신 아래 측정으로 확인했다.
- 검사 끄기 시험(scratch 복사본, worktree 무변경): 대조 P0 → 28개 통과. P1 "Enter 단계 없음" → 10개 시험 실패, P2 "입력 끝이면 통과" → 5개(입력 끝 거절 시험 전부), P3 "빈 Enter만 통과(내용 비교)" → 4개. PowerShell: 대조 D0에서 복사본 환경 탓 실패·오류 4건(.gitignore·settings·authority 경로 파일 없음 — 모든 경우에 같음) 외에, D1 "Enter 단계 없음"·D2 "`$null`이어도 진행" → 정적 시험 + Enter 블록 시험, D3 "예외면 진행" → 정적 시험이 더 실패한다.

## 측정 (이 PC, 2026-10-25, 읽기·측정만)
방법: scratch에 `tools/dev-merge.ps1` 복사본 + 호출만 적는 가짜 `devpipe.py`(MergeCopyConsoleTests와 같은 방식)를 두고 `Start-Process powershell -WindowStyle Hidden … -File <복사본> hnd-selftest -ApproveAuthority`로 실행. Python은 숨은 새 콘솔에서 `portfolio_review_journal.user_terminal_rejection()`만 부르는 자식(apply 실행 없음). 15초 뒤 끝나지 않은 프로세스는 `taskkill /T /F`. **저장소의 dev-merge.ps1과 실제 apply는 실행하지 않았다**(CLAUDE.md "Claude Code는 dev-merge·apply를 실행하지 않는다"를 지키려고 복사본으로 쟀다). 숨은 창의 화면은 콘솔 없는 별도 프로세스가 AttachConsole·ReadConsoleOutputCharacterW로 읽었다(읽기만).

| 판 | PowerShell 복사본 | 가짜 devpipe 호출 | Python 검사 |
|---|---|---|---|
| 수정 1 전(앞 Builder 끝 상태) | 1.9초에 끝남 | 1번: `merge --repo <복사본> --id hnd-selftest --approve-authority`, `_merge\` 로그 폴더 1개 | 1.2초에 끝남, isatty 참/참·핸들 참, 결과 None(통과) |
| 수정 1 후 | 15초 동안 끝나지 않음 → 종료시킴. 화면: `Authority merge. Press Enter to continue (Ctrl+C cancels):`, 커서 (59,0) | 0번, 로그 폴더 0 | 15초 동안 끝나지 않음 → 종료시킴. isatty 참/참·핸들 참(콘솔 검사는 통과), 화면: `Press Enter to apply (Ctrl+C cancels):`, 커서 (39,0) |

- 같은 측정을 두 번 했다(두 번째에 화면 읽기 추가) — 두 번 모두 같다.
- Enter 블록만 떼어 파이프로 잰 값: 빈 줄 → 진행(`[]`), 아무 글 → 진행(내용 그대로), 두 줄 → 첫 줄만, 빈 파이프·NUL → `STOP_NOT_INTERACTIVE` exit 2. 리다이렉트된 출력에서는 `Write-Host` 안내문이 stdout에 같은 줄로 붙는다(사람 창에서는 Enter의 줄바꿈 뒤에 결과 줄이 나온다).
- **Ctrl+C — 확인 필요**: 다른 프로세스에서 숨은 창에 Ctrl+C 신호(GenerateConsoleCtrlEvent)를 보냈으나 두 프로세스 모두 10초 뒤에도 Enter를 기다렸다(신호가 닿지 않은 것으로 보임, 원인 미확인). 가짜 devpipe 호출 0으로 fail closed는 유지됐다. 실제 키보드 Ctrl+C는 재지 못했다(키 입력 주입은 하지 않기로 했다). 추론: Python은 `KeyboardInterrupt`로 멈추고(시험으로 전파 고정), PowerShell은 파이프라인을 멈추거나 ReadLine이 `$null`을 돌려 STOP — 어느 쪽이든 병합 없음. 사람 시험 A-1b가 이것을 푼다.

## 한계 (수정 1 이후)
**숨은 새 콘솔/의사 콘솔/키 입력 주입은 막지 못한다. 단, 새 콘솔 창은 Enter를 기다리며 멈추므로 키 입력을 주입해야 통과한다(재입력 때와 같은 강도).** 의사 콘솔을 쥔 에이전트는 Enter(`\r`) 한 번을 써 넣으면 되고, 재입력 때도 명령줄에 있는 id/코드를 써 넣으면 됐다. GUI 자동화도 같다. Enter는 "그 창 앞에서 누군가 키를 눌렀다"만 확인한다. 그래서 CLAUDE.md 절차 규칙(Claude Code·Codex·예약·Judge는 apply 금지, Cowork는 `-ApproveAuthority`를 붙이지 않음)은 그대로 필요하다. Desktop Commander가 파이프인지 의사 콘솔인지는 여전히 확인 필요(파이프면 Enter 단계 전에 STOP, 의사 콘솔이면 Enter를 보내야 통과).

## Judge 추가 확인 대응
- **J7 통과 조건을 넓히지 않는가**: 넓히지 않는다. Python `user_terminal_rejection()`에서 Enter 단계는 isatty·GetConsoleMode 거절(851행) 뒤, 유일한 통과 반환(856행 `return None`) 바로 앞에 있고, 결과는 `None`(진행) 또는 `TERMINAL_NOT_INTERACTIVE`(거절)뿐이다 — 통과 집합 = 수정 1 전 통과 집합 ∩ "한 줄이 왔다". PowerShell도 네 조건·GetConsoleMode 블록 뒤, 블록의 마지막에 있고 STOP만 더한다(정적 시험이 순서·끝 위치 고정). 내용 비교가 없어도 안전한 이유: 비교할 값(id·코드)은 이미 명령줄에 있어 비교는 주입하는 쪽에 어려움을 더하지 않았다. 막는 힘은 "콘솔에서 한 줄을 기다린다"는 데서 오고, 그것은 그대로다. 앞선 모든 검사(isatty·핸들·네 조건·`--confirm` 일치·만료·해시·불변 조건)는 한 글자도 바뀌지 않았다.
- **J8 숨은 새 콘솔이 멈추는 코드 경로**: 숨은 새 콘솔에서는 두 표준 핸들이 진짜 콘솔이라 Python은 isatty 참/참(847행) → `standard_handles_are_console()` 참(850행 통과) → 853행 `input()`이 콘솔 읽기에서 기다림 → 제안 파일(두 CLI의 `cmd_apply`에서 이 함수 다음 줄)은 읽히지 않는다. PowerShell은 네 조건 통과(43-47행) → GetConsoleMode 참(70-73행 통과) → 80행 `[Console]::ReadLine()`에서 기다림 → python 찾기·로그 폴더·devpipe(90행 이후)에 닿지 않는다. 측정(위 표)이 이 경로와 맞다.

## 테스트 (수정 1)
명령 형식: `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"`(auto_core는 `-p "test_auto_core*"`).

| 패턴 | 기준선(수정 1 전, 앞 Builder 끝의 worktree) | 이후(수정 1 후) |
|---|---|---|
| test_approval_human_check* | Ran 24, OK | Ran 28, OK |
| test_reconcile_broker_state* | Ran 56, OK | Ran 56, OK |
| test_portfolio_review_journal* | Ran 14, OK | Ran 14, OK |
| test_decision_journal_cards* | Ran 36, OK | Ran 36, OK |
| test_dev_pipeline* | Ran 125, OK | Ran 126, OK |
| test_auto_core* | Ran 529, FAILED (failures=1, skipped=1) | Ran 529, FAILED (failures=1, skipped=1) |

- 기준선 실패·오류 이름: FAIL `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR')` 1건, ERROR 0.
- 이후 실패·오류 이름: 같은 1건뿐, ERROR 0. **새 실패 0.** skip 수 변화 없음.
- 추가(이후만): `test_language_contract*` Ran 2 OK, `test_portfolio_exposure_judge_fixes*` Ran 29 OK, `test_run_portfolio_exposure_review*` Ran 29 OK(USER_TERMINAL 문자열을 쓰는 다른 시험 모듈 — 라이브러리 자료만 쓰고 CLI apply는 부르지 않음), 스키마 감사 `validate_schema_contracts.py` PASS(errors []).

## 남은 위험 (수정 1)
1. 키 입력 주입·의사 콘솔·GUI 자동화는 막지 못한다(위 한계, 재입력 때와 같은 강도). 방어는 CLAUDE.md 절차 규칙.
2. Ctrl+C 실제 키보드 동작은 확인 필요(위 측정). 어느 경우든 병합·적용으로 넘어가는 경로는 코드상 없다(추론).
3. 숨은 새 콘솔이 Enter를 기다리며 남아 있으면(에이전트가 띄우고 버린 경우) 그 창은 사람 눈에 보이지 않은 채 계속 떠 있다. 상태 변화는 없다(제안 파일·devpipe에 닿지 않음).
4. 앞 보고의 남은 위험 2~6, 8은 그대로다.
- 바뀔 조건: Desktop Commander가 의사 콘솔이라는 측정이 나오면 Cowork 경로에서 Enter 한 번을 보내는 것만으로 통과할 수 있음이 확인된다(그래도 CLAUDE.md 규칙으로 금지). 사람 시험 A-1b에서 Ctrl+C 뒤 `MERGED`나 새 로그 폴더가 보이면 이 판단은 뒤집히고 수정이 필요하다.

# 결론
- **재입력 제거(사장이 원한 것)**: `tools/dev-merge.ps1`의 id 재입력(안내문·`[Console]::ReadLine()`·`STOP_ID_NOT_CONFIRMED`)과 두 CLI(`reconcile_broker_state.py`·`portfolio_review_journal.py` apply)의 코드 재입력(`input()`·`USER_TERMINAL_CODE_NOT_RETYPED`·안내문 상수·로케일 키)을 지웠다. `--confirm` 코드 일치 검사(라이브러리)는 그대로다.
- **대체 검사**: 기존 검사(Python `isatty() is True` 둘 다, PowerShell 네 조건)는 그대로 두고 **그 뒤에** Windows `GetConsoleMode`가 표준 입력·출력 두 핸들 모두에서 성공해야 통과한다. 실패(파이프·파일·NUL)와 예외는 기존 거절 코드(`USER_TERMINAL_NOT_INTERACTIVE` / `STOP_NOT_INTERACTIVE`)로 막는다. 우회 스위치·환경 변수·테스트 전용 분기 없음.
- **NUL 구멍**: 이 PC에서 Python은 `< NUL > NUL`을 isatty 참/참으로 보지만 GetConsoleMode는 두 핸들 모두 실패(오류 6)한다 → 이제 거절된다(실제 NUL 자식 프로세스 테스트로 고정). PowerShell 5.1은 원래부터 `[Console]::IsInputRedirected`·`IsOutputRedirected`가 NUL을 리다이렉트로 본다(측정) → PowerShell 쪽 NUL은 hnd-check 때도 막혀 있었고, GetConsoleMode는 지시문대로 넣은 이중 방어다.
- **새로 열리는 경로 — 병합 전에 꼭 볼 것**: 프로그램이 **새 콘솔 창을 띄워(숨김 창 포함, 예: `Start-Process … -WindowStyle Hidden`) 그 안에서 명령을 실행**하면 두 핸들이 진짜 콘솔이므로 모든 검사를 통과한다(측정: isatty 참/참, GetConsoleMode 1/1, IsInputRedirected·IsOutputRedirected 거짓, Host ConsoleHost, UserInteractive 참). 변경 전(HEAD b6a83e2)에는 그 숨은 창에서 재입력을 기다리며 멈췄다(측정: 15초 안에 끝나지 않아 종료시킴). 즉 재입력은 NUL만이 아니라 **"숨은 새 콘솔" 경로도 막고 있었고, GetConsoleMode는 이 경로를 막지 못한다.** 지시문 전제("재입력 대신 콘솔 핸들 검사로 같은 구멍을 막는다")는 NUL에는 맞고 이 경로에는 맞지 않는다. 지시문 범위 밖의 다른 장치는 넣지 않았다(아래 남은 위험 1에 판단 재료).
  - **수정 1 이후(2026-10-25, 사장 결정 'Enter 한 번만 누르기')**: 이 경로는 좁혀졌다. 모든 콘솔 검사를 통과한 뒤 Enter 한 번을 기다리므로, 숨은 새 콘솔은 그 자리에서 멈춘다(측정: 수정 전 복사본은 1.9초 만에 가짜 devpipe를 `--approve-authority`로 불렀고, 수정 후 복사본은 15초 동안 끝나지 않았으며 숨은 창의 화면에는 안내문과 그 뒤의 커서만 있었다 — 아래 "수정 1" 절). 이제 이 경로로 통과하려면 그 창에 키 입력을 주입해야 한다(재입력 때와 같은 강도). 입력 내용은 비교하지 않는다.
- 테스트: 기준선 대비 **새 실패 0**(알려진 PLTR 레지스트리 실패 1건만 그대로). 재입력 시험은 지우지 않고 새 동작으로 바꿨고(목록 아래), 새 시험 10개. `apply_user_confirmed_broker_snapshot.py`는 한 바이트도 안 바뀌었다(sha256 6884b197… 전후 같음).

# 한계 (hnd-check 문단 유지, NUL 항목 갱신, 새 항목 추가, 수정 1로 갱신)
**같은 Windows 계정의 GUI 자동화(화면 조작 도구)로 진짜 콘솔에 타이핑하는 에이전트는 막지 못한다. 암호학적 증명이 아니라 파이프·헤드리스 경로 차단이다. 이 한계 때문에 CLAUDE.md의 절차 규칙("Claude Code·Codex·예약·Judge는 apply 금지", "Cowork never with -ApproveAuthority")은 그대로 유지된다.**

**수정 1 이후의 정확한 한계: 숨은 새 콘솔/의사 콘솔/키 입력 주입은 막지 못한다. 단, 새 콘솔 창은 Enter를 기다리며 멈추므로 키 입력을 주입해야 통과한다(재입력 때와 같은 강도).** Enter는 "그 창 앞에서 누군가 키를 눌렀다"만 확인하고 "그 사람이 명령을 직접 쳤다"는 확인하지 않는다: 다른 프로그램이 띄운 보이는 창에서 사장이 Enter를 누르면 통과한다(재입력 때도 그 창에 id/코드를 치면 같았다).

같은 부류(역시 막지 못함):
- **새 콘솔 창(이번에 새로 통과하게 된 경로)**: 에이전트가 `Start-Process`(숨김·최소화·보이는 창 모두)나 CREATE_NEW_CONSOLE로 새 콘솔을 만들어 `reconcile_broker_state.py apply … --confirmed-via USER_TERMINAL`이나 `dev-merge.ps1 <id> -ApproveAuthority`를 실행하면 통과한다. 재입력이 있을 때는 그 창에 키를 넣을 방법(WriteConsoleInput·GUI 자동화·의사 콘솔)이 따로 필요했지만 이제는 필요 없다. 결과는 로그(`workspace/outputs/dev-runs/_merge/…`)나 상태 파일로 읽을 수 있다.
  - **수정 1 이후**: 새 콘솔 창은 모든 콘솔 검사를 통과한 뒤 Enter 안내에서 멈춘다(숨은 창 측정, 아래 "수정 1" 절). 통과하려면 다시 그 창에 키를 넣을 방법(WriteConsoleInput·GUI 자동화)이 필요하다 — 재입력 때와 같은 강도. 같은 계정의 프로그램은 숨은 콘솔에 붙을 수 있다(측정: 분리 프로세스가 AttachConsole로 숨은 창의 화면을 읽었다). 키 주입은 시험하지 않았다.
- **의사 콘솔(ConPTY)**: Windows Terminal·VS Code 터미널·node-pty류는 프로그램 입장에서 진짜 콘솔이다(GetConsoleMode도 성공). 그런 도구를 쓰는 에이전트는 통과한다(재입력이 없어져 입력 주입도 필요 없다). Desktop Commander가 파이프인지 의사 콘솔인지는 여전히 **확인 필요**(hnd-check 보고와 같음).
  - **수정 1 이후**: 의사 콘솔을 쥔 에이전트는 Enter 한 번(`\r`)을 써 넣으면 통과한다. 재입력 때 코드를 써 넣던 것과 같은 강도다(id는 명령줄에, 코드는 `--confirm`에 이미 있으므로 알아내기 어렵지 않았다).
- 숨은 콘솔에 붙어 키 입력을 주입(WriteConsoleInput)하는 프로그램 — 이제는 주입할 입력 자체가 없다. **수정 1 이후**: Enter 한 번을 주입해야 한다(막지 못함, 재입력 때와 같음).
- **NUL(갱신)**: 막는다. Windows는 `NUL`을 isatty 참으로 보지만(문자 장치) GetConsoleMode가 실패하므로 Python 두 CLI는 `USER_TERMINAL_NOT_INTERACTIVE`로 거절한다. PowerShell은 IsInputRedirected·IsOutputRedirected 단계에서 이미 막히고 GetConsoleMode에서도 막힌다(아래 측정). 한쪽만 NUL이어도 막힌다.

# 바뀐 줄 (파일:행, 변경 후 기준)
| 파일 | 행 | 내용 |
|---|---|---|
| tools/dev-merge.ps1 | 4 | Usage 머리 주석: "type the id again" → "console handles" |
| 〃 | 39-41 | 검사 주석(재입력 문구 삭제, "a new console window" 한계 추가) |
| 〃 | 42-46 | 네 조건 검사 — **무변경** |
| 〃 | 47-72 | 신규: `Add-Type`(ASCII C# `DevMergeConsoleHandles`, kernel32 `GetStdHandle`·`GetConsoleMode` P/Invoke) → `Both()`가 -10·-11 두 핸들 모두 성공해야 참. `try/catch`(만들기·호출 예외 → `$false`), `-ne $true`면 `STOP_NOT_INTERACTIVE` exit 2 |
| 〃 | (삭제, 변경 전 47-55) | 안내문 `$ask`(유니코드 이스케이프 3조각)·`Write-Host -NoNewline`·`[Console]::ReadLine() -cne $Id`·`STOP_ID_NOT_CONFIRMED` |
| manage-us-stock-strategy/scripts/portfolio_review_journal.py | 17 | 모듈 설명(apply 줄): "the code typed once more" → "run by hand in an interactive console only, no pipe or NUL" |
| 〃 | 68-72 | 상수: `TERMINAL_NOT_INTERACTIVE` 유지, `TERMINAL_CODE_NOT_RETYPED`·`TERMINAL_RETYPE_PROMPT` 삭제, `STD_INPUT_HANDLE`(0xFFFFFFF6)·`STD_OUTPUT_HANDLE`(0xFFFFFFF5) 추가 |
| 〃 | 803-829 | 신규 `standard_handles_are_console()` |
| 〃 | 832-848 | `user_terminal_rejection()`: 인자 없음(이전 `confirm_code`, `prompt`), `input()`·EOFError·비교 삭제, isatty 뒤에 `standard_handles_are_console() is not True`면 거절 |
| 〃 | 855 | `cmd_apply`: `user_terminal_rejection(args.confirm)` → `user_terminal_rejection()` |
| manage-us-stock-strategy/scripts/reconcile_broker_state.py | 8-10 | 모듈 설명(apply 줄) |
| 〃 | 286-291 | `cmd_apply` USER_TERMINAL 분기: import에서 `TERMINAL_NOT_INTERACTIVE` 삭제, 안내문 인자 삭제, 결과가 None이 아니면 `apply_terminal_not_interactive`·반환 2(이전의 "다른 거절 → `apply_rejected`" 분기는 거절 사유가 하나뿐이라 삭제) |
| manage-us-stock-strategy/assets/locales/reconcile-broker-state-ko-KR.json | 52 | `apply_terminal_retype` 키 삭제, 52행 끝 쉼표 정리 |
| manage-us-stock-strategy/references/broker-snapshot-reconciliation.md | 180-184 | 3절 Fallback 문단: "대화형 콘솔에서 직접 실행", 콘솔 핸들(GetConsoleMode)·NUL 거절, "The code is not typed again", 한계에 "a program that opens a new console window" 추가 |
| tools/dev_pipeline/README.md | 11, 44, 70 | 11: 대화형 창에서 직접 실행, 거절 조건에 NUL·GetConsoleMode, "id 재입력은 없다"(`STOP_ID_NOT_CONFIRMED` 삭제, "이 대화의 사장 결정"·"Cowork는 -ApproveAuthority를 붙이지 않는다" 유지). 44: 수동 경로 병합 스크립트 규칙 = 같은 콘솔 확인(네 조건 + 두 핸들 GetConsoleMode, 실패도 중단), id 재입력 요구 안 함. 70: "+ id 재입력" → "직접 실행" |
| manage-us-stock-strategy/tests/test_approval_human_check.py | 전체 | 아래 시험 목록 |
| manage-us-stock-strategy/tests/test_dev_pipeline.py | 1296-1327 | 정적 검사 갱신 |
| 〃 | 1529-1545 | `run_copy`에 `nul`·`script` 인자(기존 호출 동작 같음) |
| 〃 | 1569-1597 | 새 시험 2개 |
| docs/claude/hnd-check2-report.md | 전체 | 이 보고(신규) |

`test_reconcile_broker_state.py`·`test_portfolio_review_journal.py`·`test_decision_journal_cards.py`는 **바꾸지 않았다**(허용 목록에는 있음). 세 곳 모두 `user_terminal_rejection`을 `return_value=None`으로 patch하고 있어 인자가 없어져도 그대로 맞다.

모든 바뀐 파일 CRLF 유지(bare LF 0 측정), `.py`·`.ps1`은 ASCII(비ASCII 바이트 0 측정), 로케일 JSON 파싱 확인. 허용 목록 밖 파일 변경 0(`git status`: 위 8개 + 이 보고).

# 제거한 기능
1. dev-merge.ps1: id 재입력 안내문·읽기·비교·`STOP_ID_NOT_CONFIRMED`.
2. portfolio_review_journal.py: 코드 재입력(`input()`), `USER_TERMINAL_CODE_NOT_RETYPED`, `TERMINAL_RETYPE_PROMPT`, `user_terminal_rejection`의 두 인자.
3. reconcile_broker_state.py: 재입력 안내문 전달, 재입력 거절을 `apply_rejected`로 내던 분기.
4. 로케일 키 `apply_terminal_retype`.
- 쓰는 곳이 없어진 것만 지웠다: 이 worktree 전체 grep(`STOP_ID_NOT_CONFIRMED|USER_TERMINAL_CODE_NOT_RETYPED|TERMINAL_RETYPE|apply_terminal_retype|ReadLine`)에서 남은 것은 `docs/claude/hnd-check-report.md`(앞 변경의 기록, 손대지 않음), README의 부정문("id 재입력은 없다"), 정적 테스트의 "없어야 한다" 단언뿐이다.

# 시험 목록 (지운 시험 0, skip 추가는 Windows 전용 새 시험만)
## 바꾼 시험 (재입력 시험 → 새 동작)
| 이전 | 이후 | 바뀐 단언 |
|---|---|---|
| TerminalCheckTests.test_the_code_is_typed_once_more | test_a_console_goes_on_without_reading_anything | 맞는/틀린/빈 줄/입력 끝 → 재입력 판정 대신 "모두 통과, stdin 0바이트 읽음, 출력 없음" |
| TerminalCheckTests.test_no_bypass_input_in_the_check | (같은 이름) | 인자 기대값 `["confirm_code","prompt"]` → `[]`, 두 함수 모두 검사, 금지어에 `input(` 추가 |
| ReconcileApplyTests.test_console_apply_needs_the_same_code_again | test_console_handles_are_needed_too | 재입력 불일치 거절 → isatty 참·핸들 실패 거절(`apply_terminal_not_interactive`, 상태·감사 파일 무변경) |
| ReconcileApplyTests.test_retyping_never_replaces_the_code_check | test_the_console_check_never_replaces_the_code_check | 재입력 인자만 삭제. 단언(`CONFIRM_CODE_MISMATCH`, 무변경) 그대로 |
| ReconcileApplyTests.test_console_apply_with_the_code_typed_again_applies | test_console_apply_goes_on_without_typing_the_code | 안내문 단언 → `input()`이 불리면 실패 + 출력이 적용 성공 문구로 시작. revision 8·원장(USER_TERMINAL, 코드) 단언 그대로 |
| ReconcileApplyTests.test_refused_before_the_proposal_is_read | (같은 이름) | 기존 경우(비대화형) 유지 + 핸들 실패 경우 추가 |
| JournalApplyTests.test_an_existing_journal_stays_byte_identical | (같은 이름) | 두 번째 경우 "재입력 틀림" → "핸들 실패". 첫 경우·바이트 동일 단언 그대로 |
| JournalApplyTests.test_console_apply_needs_the_same_code_again | test_console_handles_are_needed_too | 위 reconcile과 같음(일지 파일 안 생김) |
| JournalApplyTests.test_console_apply_with_the_code_typed_again_records | test_console_apply_records_without_typing_the_code | 위 reconcile과 같음(항목 1개, USER_TERMINAL) |
| StaticScriptTests.test_merge_authority_needs_an_interactive_console | (같은 이름) | 지운 단언: `ReadLine -cne $Id` 블록, `STOP_ID_NOT_CONFIRMED`, `Write-Host -NoNewline $ask`, 안내문 한국어 디코드 일치(기능 제거). 더한 단언: 네 조건 블록 → Add-Type 블록 → catch=`$false` → `-ne $true`면 STOP 순서, C#이 -10·-11 둘 다 요구, DllImport 2개, 블록의 STOP_NOT_INTERACTIVE 2개, `ReadLine`·`Read-Host`·`Write-Host`·`STOP_ID_NOT_CONFIRMED`·`Unescape`가 파일에 없음. 그대로: 위치(id 형식 검사 뒤·`$repo` 앞), `$ApproveAuthority` 3회, param은 Id·ApproveAuthority뿐, `$env:`는 ComSpec·SystemRoot뿐, 블록에 test·bypass·skip·`$env:` 없음 |
- 기존 클래스 setUp에 `standard_handles_are_console` patch(통과) 1개씩 — 같은 프로세스 안 시험은 자기 콘솔이 없기 때문(대화형 가정). 실제 핸들 시험은 patch 없이 자식 프로세스로 돈다.
- 그대로 둔 시험(단언 무변경): `test_both_streams_must_be_a_terminal`(호출 순서 단언 1줄 추가: isatty가 먼저 거절하면 핸들 검사는 안 불림), `test_missing_closed_or_unclear_streams_are_not_a_terminal`, 두 클래스의 `test_terminal_apply_without_a_console_is_refused`, `test_cowork_path_is_unchanged_without_a_console`, `test_cowork_path_still_needs_the_user_message`, `MergeCopyConsoleTests`의 기존 2개(스위치 없음 회귀, 스위치 + 비대화형 → STOP_NOT_INTERACTIVE).

## 새 시험 10개
| 시험 | 무엇을 |
|---|---|
| TerminalCheckTests.test_terminal_streams_without_console_handles_are_refused | isatty 참/참인데 핸들 검사가 False·None·1·"True"·MagicMock → 거절(True만 통과), stdin 안 읽음 |
| ConsoleHandleTests.test_both_standard_handles_must_be_console_handles (Windows) | 가짜 kernel32: (1,1)만 참, (0,1)(1,0)(0,0) 거짓. 묻는 핸들 id가 정확히 (DWORD)-10, -11 |
| ConsoleHandleTests.test_an_error_or_an_unclear_answer_is_refused (Windows) | OSError·ctypes.ArgumentError·TypeError·None·"1"·MagicMock 답, kernel32 불러오기 실패 → 거짓 |
| ConsoleHandleTests.test_off_windows_isatty_is_the_whole_check | Windows가 아니면 kernel32를 부르지 않고 참(isatty만) |
| RealHandleTests.test_nul_looks_like_a_terminal_but_is_refused (Windows) | **실제 NUL** 자식 프로세스: isatty [참,참], 핸들 거짓, 거절 |
| RealHandleTests.test_pipes_files_and_half_nul_are_refused (Windows) | NUL 입력+파이프 출력, 파이프 입력+NUL 출력, 파일 입출력 → 모두 거절 |
| ReconcileApplyTests.test_terminal_apply_with_nul_is_refused_end_to_end (Windows) | 실제 `reconcile_broker_state.py apply … USER_TERMINAL`을 NUL 입출력 자식 프로세스로: 반환 2, stderr 없음, 상태·감사 파일 무변경(임시 폴더) |
| JournalApplyTests.test_terminal_apply_with_nul_is_refused_end_to_end (Windows) | 실제 `portfolio_review_journal.py apply … USER_TERMINAL`을 NUL로: 반환 2, stderr 없음, 일지 안 생김(임시 폴더) |
| MergeCopyConsoleTests.test_authority_switch_with_nul_stops | 임시 복사본 dev-merge + 가짜 devpipe를 NUL 입출력으로: `-ApproveAuthority` → exit 2, devpipe 호출 0, run 폴더 0. 같은 NUL에서 스위치 없으면 가짜 devpipe까지 감(→ 멈춘 곳은 콘솔 검사) |
| MergeCopyConsoleTests.test_console_handle_check_builds_and_refuses_redirected_handles | 다른 시험은 모두 네 조건에서 멈춰 GetConsoleMode에 닿지 않으므로, 복사본 스크립트의 Add-Type 블록을 글자 그대로 떼어 Windows PowerShell에서 만들고 호출: 컴파일 성공, NUL 입력+파이프 출력·NUL/NUL 모두 `False` |

- 검사 끄기 시험(scratch 복사본, worktree 소스 무변경): 대조(변경 없음) 복사본에서는 JournalApplyTests 6개만 오류(복사본에 `stock-strategy-system/alert_policy.json`이 없음 — 환경). 그 밖에 M1 "핸들 검사가 늘 참" → 5개 실패(ConsoleHandleTests 2, RealHandleTests 2, reconcile 끝-끝 NUL 1), M2 "거절이 핸들 검사를 무시" → 7개 실패(TerminalCheck 2, reconcile 4, RealHandle NUL 1). 새 시험이 검사를 실제로 붙잡는다. 일지 쪽은 같은 함수를 쓰지만 복사본 환경 때문에 이 방법으로는 재지 못했다.

# 새 검사 규칙 (요약)
1. **Python `user_terminal_rejection()`** (`--confirmed-via USER_TERMINAL`일 때만, 제안 파일을 읽기 전):
   - a. `sys.stdin.isatty() is True and sys.stdout.isatty() is True` — 무변경(스트림 없음·닫힘·예외 → 비대화형).
   - b. (신규, a가 통과할 때만) `standard_handles_are_console() is True`. Windows(`os.name == "nt"`): `ctypes.WinDLL("kernel32")`의 `GetStdHandle(STD_INPUT_HANDLE)`·`GetStdHandle(STD_OUTPUT_HANDLE)` 각각에 `GetConsoleMode`가 0이 아닌 정수를 돌려줘야 참. 0·정수 아님·예외(AttributeError, OSError, TypeError, ValueError, ctypes.ArgumentError)·ctypes import 실패 → 거짓. Windows가 아니면 참(isatty만, 테스트 환경).
   - c. a 또는 b 실패 → `USER_TERMINAL_NOT_INTERACTIVE`. reconcile은 `apply_terminal_not_interactive` 한 줄·반환 2, journal은 `기록하지 않았습니다: USER_TERMINAL_NOT_INTERACTIVE`·반환 2.
   - d. 통과하면 기존 흐름 그대로. stdin을 읽지 않고 안내문도 없다. 코드 일치·만료·해시·불변 조건 검사는 라이브러리에서 그대로.
   - **수정 1 이후** d 대신: a·b가 통과하면 `input("Press Enter to apply (Ctrl+C cancels): ")` 한 번(상수 `TERMINAL_ENTER_PROMPT`). 돌려받은 줄은 변수에 담지 않는다(비교 불가, 정적 시험으로 고정). `EOFError`(입력 끝) → c와 같은 `USER_TERMINAL_NOT_INTERACTIVE`. `KeyboardInterrupt`는 잡지 않는다(파이썬 기본대로 멈춤). 그 밖의 읽기 오류(OSError·ValueError)는 두 CLI `cmd_apply`의 기존 except가 거절(반환 2)로 처리한다. 그 뒤 기존 흐름 그대로(제안 파일 읽기는 이 다음).
2. **dev-merge.ps1** (`-ApproveAuthority`가 있을 때만, id 형식 검사 바로 뒤, python 찾기·로그 폴더·devpipe 전):
   - a. 네 조건(IsInputRedirected·IsOutputRedirected·`$Host.Name -ne 'ConsoleHost'`·`-not UserInteractive`) — 무변경, 하나라도 걸리면 `DEV-MERGE <id> STOP_NOT_INTERACTIVE` exit 2.
   - b. (신규) `Add-Type`로 `DevMergeConsoleHandles.Both()` = `GetConsoleMode(GetStdHandle(-10)) && GetConsoleMode(GetStdHandle(-11))`. Add-Type·호출 예외 → `$false`. `-ne $true`면 같은 STOP exit 2.
   - c. 통과하면 기존 흐름(devpipe `merge … --approve-authority`). 스위치가 없으면 블록 전체가 돌지 않는다. 종료 코드 0/2/3·출력 첫 줄 형식 그대로. 새 param·환경 변수·테스트 분기 없음(정적 테스트로 고정).
   - **수정 1 이후** b와 c 사이: `Write-Host -NoNewline 'Authority merge. Press Enter to continue (Ctrl+C cancels): '` 뒤 `[Console]::ReadLine()` 한 번. `$null`(입력 끝)이거나 안내·읽기 예외(catch → `$null`)면 같은 `STOP_NOT_INTERACTIVE` exit 2. 그 밖에는 내용과 상관없이 c로. 새 종료 코드·새 STOP 이름 없음. `$entered`는 4번만 나온다(초기화·읽기·catch·`$null` 검사, 정적 시험으로 고정) — 비교에 쓰이지 않는다.
3. **통과 조건**: 새 검사는 거절만 더한다. 넓어진 것은 재입력 제거 하나뿐(사장 결정)이며, 그 결과 "진짜 콘솔에서 아무것도 치지 않은 실행"이 통과한다 — 사람의 창과 함께 프로그램이 띄운 새 콘솔도(한계·남은 위험 1). **수정 1 이후**: "아무것도 치지 않은 실행"은 더는 통과하지 않는다 — Enter 한 번(또는 아무 줄)이 와야 한다. 통과 조건 = 수정 1 전 통과 조건 ∩ "Enter가 왔다"(J7).
4. COWORK·AUTO_CORE·일반 병합 경로: 실행되는 줄 무변경(검사는 USER_TERMINAL 분기·`if ($ApproveAuthority)` 안에만). `test_cowork_path_is_unchanged_without_a_console` 2개(검사 함수가 불리면 실패)와 `test_general_merge_without_the_switch_is_unchanged`가 통과.

# NUL 측정 결과 (이 PC, 2026-10-25, 읽기·측정만, 상태 변경 없음)
환경: Windows 11 Pro 10.0.26200, Python 3.13.15, Windows PowerShell 5.1.26100.9711. 측정 스크립트는 scratch(저장소 밖)에서만 돌렸다.

| 실행 형태 | Python isatty (입력/출력) | Python GetConsoleMode (입력/출력) | PS IsInputRedirected / IsOutputRedirected | PS GetConsoleMode (입력/출력) |
|---|---|---|---|---|
| `cmd /c "… < NUL > NUL"` | 참/참 | 0/0 (오류 6) | 참/참 | 거짓/거짓 (오류 6) |
| 파이프(이 에이전트 셸) | 거짓/거짓 | 0/0 | 참/참 | 거짓/거짓 |
| 파일 리다이렉트 | 거짓/거짓 | 0/0 | (재지 않음) | (재지 않음) |
| 새 콘솔 창(숨김) | 참/참 | 1/1 | 거짓/거짓 | 참/참 |
| 새 콘솔 + `< NUL`만 | 참/참 | 0/1 | 참/거짓 | 거짓/참 |
| 새 콘솔 + `> NUL`만 | 참/참 | 1/0 | (재지 않음) | (재지 않음) |

- 파일 종류(GetFileType): NUL = 문자 장치(2), 파이프 3, 파일 1. NUL은 콘솔과 같은 "문자 장치"라서 isatty가 참이 된다.
- PowerShell `[Console]::IsInputRedirected`는 NUL을 리다이렉트로 본다(지시문의 "확인 필요" 해소). 측정값은 .NET이 문자 장치에서 GetConsoleMode를 확인한다는 것과 맞다(추론, .NET 소스는 이 세션에서 열지 않음).
- 변경 후 측정: Python `user_terminal_rejection()` — `< NUL > NUL`에서 isatty 참/참이지만 `USER_TERMINAL_NOT_INTERACTIVE`, 숨은 새 콘솔에서 즉시 `None`(통과). dev-merge.ps1의 Add-Type 블록을 글자 그대로 떼어 실행 — 숨은 새 콘솔 `True`, `< NUL > NUL` `False`.
- 변경 전(HEAD) 측정: 숨은 새 콘솔에서 `user_terminal_rejection("PROBE123")`이 15초 안에 돌아오지 않음(입력 대기) → 강제 종료.
- Add-Type: 처음 0.1초 안팎. 같은 창에서 같은 소스로 두 번 → 문제없음. 같은 형식 이름에 다른 소스 → 예외(→ STOP, 새 창이면 해결. 남은 위험 5).

# 테스트
명령 형식: `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"`(auto_core는 `-p "test_auto_core*"`).

| 패턴 | 기준선(수정 전, HEAD b6a83e2, 깨끗한 worktree) | 이후 |
|---|---|---|
| test_approval_human_check* | Ran 16, OK | Ran 24, OK |
| test_reconcile_broker_state* | Ran 56, OK | Ran 56, OK |
| test_portfolio_review_journal* | Ran 14, OK | Ran 14, OK |
| test_decision_journal_cards* | Ran 36, OK | Ran 36, OK |
| test_dev_pipeline* | Ran 123, OK | Ran 125, OK |
| test_auto_core* | Ran 529, FAILED (failures=1, skipped=1) | Ran 529, FAILED (failures=1, skipped=1) |

- 기준선 실패·오류 이름: FAIL `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR')` 1건. ERROR 0.
- 이후 실패·오류 이름: 위와 같은 1건뿐(PLTR). ERROR 0. **새 실패 0.** skip 수 변화 없음(auto_core 1 → 1, 나머지 패턴 0 → 0: 새 Windows 전용 시험은 이 PC에서 모두 실행됨).
- 추가: `test_language_contract*` Ran 2 OK(scripts/*.py ASCII), 스키마 감사 `validate_schema_contracts.py` PASS(errors []).
- 바뀐 모듈을 import하는 다른 시험 11개 모듈(test_future_order_shadow, test_cash_flow_evidence, test_v2_6_broker_beginner, test_v2_5_broker_snapshot, test_state_write_boundary, test_score_ticket_outcomes, test_score_learning, test_s1b_plan_b_no_data_pass, test_run_portfolio_exposure_review, test_portfolio_exposure_judge_fixes, test_materialize_kiwoom_session_aware_acceptance_candidate): 이후 Ran 257, failures=1, errors=1 — 둘 다 `test_materialize_kiwoom_session_aware_acceptance_candidate`(test_05·test_12)이고 메시지는 9개 모두 `source artifact missing: …`(worktree에 없는 git 무시 산출물). 그 모듈·스크립트·assets/*.json 어디에도 바뀐 파일 이름이 없다(grep 0건) → 이 변경과 무관. 이 11개의 변경 전 기준선은 재지 않았다(HEAD `git archive` 사본은 workspace/가 없어 26개 전부 오류라 비교가 안 됨).
- 전체 스위트(`-p "test*.py"`)는 돌리지 않았다: 지시문의 비교 대상은 위 6개 패턴이고, 바뀐 모듈을 import하는 나머지 11개는 위처럼 따로 돌렸다.

# 남은 위험
1. **새 콘솔 창 경로(가장 중요)**: 위 한계 첫 항목. 프로그램이 새 콘솔(숨김 포함)을 띄우면 USER_TERMINAL apply와 `-ApproveAuthority` 병합이 입력 없이 통과한다. 변경 전에는 그 창에서 재입력을 기다려 막혔다(측정). 이제 이 경로의 방어는 CLAUDE.md 절차 규칙뿐이다(Claude Code 세션에는 settings의 명령 거부 규칙도 걸리지만, 그것이 이 경로를 막는지는 이 세션에서 settings 파일을 열지 않아 확인 필요).
   - 판단 재료(이번에 넣지 않음, 지시문 범위 밖): ① 그대로 병합(사장 결정대로, 위 위험 수용) ② 병합 보류 — hnd-check 상태(재입력 있음) 유지 ③ 다른 장치를 별도 변경으로 검토 — 예: 콘솔 창이 화면에 보이는지·전면 창인지 확인. 다만 Windows Terminal(Windows 11 기본 터미널) 안의 PowerShell은 의사 콘솔이라 그런 확인이 사람 창까지 막을 수 있다(미측정, 확인 필요). 보이는 새 창도 잠깐 뜨면 통과하므로 완전한 차단도 아니다.
   - 바뀔 조건: 사장 결정 카드('id 재입력만 없애기', 2026-10-25 06:55Z)가 이 경로를 이미 알고 받아들였다는 기록이 있으면 ①로 정리된다(카드 원문은 이 세션에서 열지 않았다). Windows Terminal에서 창 확인 방식이 사람 창을 막지 않는다는 측정이 나오면 ③이 현실적이 된다.
   - **수정 1 이후**: 사장 결정 카드 'Enter 한 번만 누르기'(2026-10-25 08:22Z, 수정 1 지시문 source 줄로만 확인 — 카드 원문은 이 세션에서 열지 않았다)대로 Enter 확인을 넣었다. 숨은 새 콘솔은 이제 Enter에서 멈춘다(측정). 남은 것은 키 입력 주입·의사 콘솔·GUI 자동화(재입력 때와 같은 강도)와 CLAUDE.md 절차 규칙이다. 위 ①②③은 수정 1로 대부분 정리되고, ③(창 확인)은 여전히 별도 변경 후보일 뿐이다.
2. 의사 콘솔·GUI 자동화는 전과 같이 못 막는다. Desktop Commander가 파이프인지 의사 콘솔인지는 확인 필요(파이프라면 STOP, 의사 콘솔이라면 통과).
3. 수동 경로 병합 스크립트(`docs/claude/<id>-merge-*.ps1`)는 코드로 강제되지 않는다(README 44행 규칙만) — hnd-check 남은 위험 2와 같다. 이번 지시문도 새 .ps1을 허용하지 않아 공용 검사 조각은 만들지 않았다.
4. 재입력을 설명하는 문서가 허용 목록 밖에 남아 있다: `docs/claude/hnd-check-report.md`(앞 변경의 기록이라 고치지 않는 것이 맞다). 메인 체크아웃 `docs/claude/` grep(`STOP_ID_NOT_CONFIRMED|USER_TERMINAL_CODE_NOT_RETYPED|id 재입력|코드 재입력|한 번 더 입력|id를 그대로 입력`)에서는 `hnd-check-builder-prompt.md`·`hnd-check2-builder-prompt.md`·`hnd-check-report.md` 3개뿐(모두 지시문·기록). 다른 표현으로 재입력을 적은 문서가 있는지는 이 패턴 밖이라 확인 필요. Cowork가 관제판·결정 기록에 "재입력 없음"을 반영할 후보.
5. Add-Type 형식 이름 충돌: 같은 PowerShell 창에서 이 스크립트의 다른 판(C# 소스가 다른 판)을 먼저 돌린 뒤 새 판을 돌리면 `STOP_NOT_INTERACTIVE`(fail closed). 새 창을 열면 해결. 같은 판을 두 번 돌리는 것은 문제없음(측정).
6. Windows Terminal·VS Code 안의 PowerShell 창에서 사람 경로가 통과하는지는 이 PC에서 재지 않았다(확인 필요). 이론상 의사 콘솔도 콘솔 핸들이라 GetConsoleMode가 성공하고, PowerShell 쪽은 IsInputRedirected가 이미 같은 확인을 하므로 hnd-check에서 통과하던 창은 그대로 통과할 것으로 본다(추론). 아래 사람 시험 A-1이 이것을 확인한다.
7. 사장 손: 권한 병합·USER_TERMINAL apply 1건당 입력이 id/코드 재입력 1줄 줄어든다(명령 1줄만). 주간 일상 손 0 그대로. **수정 1 이후**: 명령 1줄 + Enter 한 번(내용 입력 없음). 주간 일상 손 0 그대로.
8. 새 시험 중 실제 핸들·복사본 실행 시험은 python/powershell.exe 자식 프로세스를 띄운다(각 1초 안팎). Windows가 아닌 곳에서는 skip(선례와 같음). 이 PC에서는 모두 실행됨(skip 수 변화 0).

# 사람이 한 번 해 볼 시험 절차 (병합 뒤, 1회, 선택 — 재입력 없음, 수정 1로 갱신: Enter 한 번)
모두 **없는 id·없는 제안 파일**을 써서 상태·일지·병합이 바뀔 수 없다. 창: 시작 메뉴 → **Windows PowerShell**(ISE 아님). 먼저 `cd "E:\사업\##금동한\코덱스저장소"`.

A. dev-merge 권한 병합 검사
1. `.\tools\dev-merge.ps1 hnd-selftest -ApproveAuthority` → `Authority merge. Press Enter to continue (Ctrl+C cancels): ` 안내가 나오고 멈춘다. Enter를 누르면 `DEV-MERGE hnd-selftest STOP_NO_RESULT reason=result.json`(그런 run이 없음). 병합 없음. `workspace\outputs\dev-runs\_merge\` 아래 로그 폴더 1개만 생긴다(git 무시 폴더). (Windows Terminal 창에서도 한 번 해 보면 남은 위험 6이 풀린다.)
1b. (수정 1, 선택) 같은 명령에서 안내가 나오면 **Ctrl+C** → `STOP_NO_RESULT`·`MERGED` 줄 없이 끝나거나 `DEV-MERGE hnd-selftest STOP_NOT_INTERACTIVE`. `_merge\` 아래 새 로그 폴더가 없어야 한다(아래 "수정 1" 측정의 확인 필요 항목을 푼다).
2. 파이프: `"x" | powershell -NoProfile -File .\tools\dev-merge.ps1 hnd-selftest -ApproveAuthority` → `DEV-MERGE hnd-selftest STOP_NOT_INTERACTIVE`.
3. NUL(입력만): `cmd /c "powershell -NoProfile -File .\tools\dev-merge.ps1 hnd-selftest -ApproveAuthority < NUL"` → `DEV-MERGE hnd-selftest STOP_NOT_INTERACTIVE`.
4. NUL(입출력 둘 다, 출력은 보이지 않음): `cmd /c "powershell -NoProfile -File .\tools\dev-merge.ps1 hnd-selftest -ApproveAuthority < NUL > NUL"` → 화면에 아무것도 없음. 이어서 `$LASTEXITCODE` → `2`. `_merge\` 아래 새 로그 폴더가 생기지 않았는지 확인.

B. 대조 apply(USER_TERMINAL) 검사
1. `python manage-us-stock-strategy/scripts/reconcile_broker_state.py apply --confirm TESTONLY --confirmed-via USER_TERMINAL --proposal C:\no-such-folder\x.json` → `Press Enter to apply (Ctrl+C cancels): ` 안내가 나오고 멈춘다. Enter를 누르면 `적용하지 않았습니다: …`(없는 제안 파일 오류). 상태 변화 없음. (선택) 안내에서 Ctrl+C → 파이썬 `KeyboardInterrupt`로 멈춘다(적용 없음).
2. NUL: `cmd /c "python manage-us-stock-strategy/scripts/reconcile_broker_state.py apply --confirm TESTONLY --confirmed-via USER_TERMINAL --proposal C:\no-such-folder\x.json < NUL"` → 안내 없이 `적용하지 않았습니다: 사장 터미널에서 직접 실행하고 Enter를 한 번 눌러야 합니다(대화형 콘솔 아님 — …)`(수정 1에서 문구 갱신). (변경 전에는 여기서 재입력 단계의 입력 끝으로 `USER_TERMINAL_CODE_NOT_RETYPED`였다.)
3. 파이프: `"TESTONLY" | python manage-us-stock-strategy/scripts/reconcile_broker_state.py apply --confirm TESTONLY --confirmed-via USER_TERMINAL --proposal C:\no-such-folder\x.json` → 2와 같은 문구.

C. 일지 apply(USER_TERMINAL) 검사
1. `python manage-us-stock-strategy/scripts/portfolio_review_journal.py apply --proposal C:\no-such-folder\p.json --confirm TESTONLY --confirmed-via USER_TERMINAL --journal C:\no-such-folder\j.json` → `Press Enter to apply (Ctrl+C cancels): ` 안내 → Enter → `기록하지 않았습니다: …`(없는 제안 파일 오류).
2. NUL: 같은 명령을 `cmd /c "… < NUL"`로 → `기록하지 않았습니다: USER_TERMINAL_NOT_INTERACTIVE`.

# 지킨 것 (J1~J8 대응, J7·J8과 수정 1 항목은 "수정 1" 절에 자세히)
- 수정 1: 바뀐 파일은 같은 허용 목록 안(dev-merge.ps1, README, portfolio_review_journal.py, reconcile_broker_state.py(설명 문자열만), 로케일, reference, test_approval_human_check.py, test_dev_pipeline.py, 이 보고). 지운 시험 0, 지운 단언은 "읽지 않는다·안내문 없다"(수정 1로 없어진 동작)의 것뿐. CRLF·ASCII 재측정 통과. 저장소의 dev-merge.ps1·실제 apply는 실행하지 않았다(측정은 scratch 복사본 + 가짜 devpipe, Python은 `user_terminal_rejection()`만 호출).
- J7: Enter 단계는 앞선 모든 검사 **뒤**, 기존 통과 분기(`return None` / devpipe 실행) 바로 앞에만 있고 거절만 더한다. 읽은 줄은 담지 않거나(`input()`) `$null` 검사에만 쓴다(`$entered` 4회) — 정적 시험으로 고정.
- J8: 숨은 새 콘솔 → 콘솔 검사 모두 통과 → Enter 대기에서 멈춤(코드 경로와 측정은 "수정 1" 절).
- J1: 변경은 허용 목록 안 파일뿐(dev-merge.ps1, README, reconcile_broker_state.py, portfolio_review_journal.py, 로케일, reference, test_approval_human_check.py, test_dev_pipeline.py, 이 보고). `apply_user_confirmed_broker_snapshot.py` 무변경.
- J2: 재입력 제거 외 경로 무변경 — COWORK·AUTO_CORE·propose·show·auto·일반 병합 줄 그대로(위 규칙 4).
- J3: 새 검사는 거절만 더함. NUL·파일·파이프는 Python(실제 자식 프로세스 시험 4개)과 PowerShell(복사본 NUL 시험·C# 블록 시험) 양쪽에서 막힘. 재입력 제거로 넓어진 부분(새 콘솔 창)은 숨기지 않고 결론·한계·남은 위험 1에 적음.
- J4: 지운 단언은 제거된 기능(재입력·안내문·STOP_ID_NOT_CONFIRMED)의 것뿐(위 표). skip 추가는 Windows 전용 새 시험뿐.
- J5: 한계 문단 유지 + 새 콘솔 창 항목 추가 + NUL 항목 갱신.
- J6: CRLF·ASCII 측정(위).
- 실행하지 않은 것: auto_core.py, 실제 상태·일지 대상 reconcile/journal apply(시험은 임시 폴더의 합성 제안만), dev-run·dev-merge·dev-queue(저장소의 dev-merge.ps1은 실행 안 함 — 시험이 임시 폴더 복사본과 거기서 떼어 낸 C# 블록만 돌림), 키움 없음, 비밀 파일 읽기 없음, git add·commit·push·브랜치 변경 없음. 측정 중 띄운 숨은 창은 측정용 Python·PowerShell 스크립트(scratch)뿐이다.
