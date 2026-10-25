---
id: hnd-check2-fix1-prompt
title: "hnd-check2 수정 1 — 재입력 대신 'Enter 한 번' 확인 추가"
date: 2026-10-25
class: "권한·한도(K3) 후속, 같은 worktree hnd-check2에서 이어서 수정"
source: "사장 결정 카드 'Enter 한 번만 누르기'(2026-10-25 08:22Z). 근거: docs/claude/hnd-check2-report.md '새로 열리는 경로' — 재입력이 없으면 숨은 새 콘솔 창이 검사를 통과한다"
authority: "order_authority=false · quantity_authority 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음 · CLAUDE.md 수정 없음"
---

# 수정 1: Enter 한 번 확인

hnd-check2-builder-prompt.md의 모든 규칙(허용 파일, 지켜야 할 것, CRLF·ASCII, 실행 금지, 커밋 금지)이 그대로 적용된다. 이 worktree의 현재 변경 위에서 아래만 바꾼다. 먼저 docs/claude/hnd-check2-report.md "새로 열리는 경로"를 읽는다.

## 바꿀 내용
재입력(문자열 비교)은 **되살리지 않는다.** 대신 모든 콘솔 검사를 통과한 **뒤에**, 사람이 키보드 앞에 있다는 확인으로 **Enter 한 번**을 요구한다. 입력 내용은 비교하지 않는다(빈 줄이든 아무 글자든 Enter면 진행).

1. **tools/dev-merge.ps1** (`-ApproveAuthority`일 때만, GetConsoleMode 검사 뒤, devpipe 실행 전):
   - 화면에 `Authority merge. Press Enter to continue (Ctrl+C cancels): ` 같은 ASCII 안내(`Write-Host -NoNewline`)를 보이고 `[Console]::ReadLine()`을 한 번 호출한다.
   - 반환이 `$null`(입력 끝)이면 `DEV-MERGE <id> STOP_NOT_INTERACTIVE`, exit 2. 그 밖에는 내용과 상관없이 계속한다. 예외도 같은 STOP(fail closed).
   - 한국어 안내문이 필요하면 기존 방식(유니코드 이스케이프)을 쓰되 ASCII 안내로 충분하면 그대로 둔다. 새 종료 코드·새 STOP 이름 없음.
2. **reconcile_broker_state.py·portfolio_review_journal.py `cmd_apply`** (`--confirmed-via USER_TERMINAL`일 때만, isatty·GetConsoleMode 통과 뒤, 제안 파일 읽기 전):
   - `input("Press Enter to apply (Ctrl+C cancels): ")` 한 번. `EOFError`(입력 끝)이면 기존 거절 `USER_TERMINAL_NOT_INTERACTIVE`와 같은 방식(reconcile: `apply_terminal_not_interactive` 안내·반환 2, journal: `journal_apply_rejected` 형식·반환 2). 내용은 비교하지 않는다. `KeyboardInterrupt`는 건드리지 않는다.
   - `--confirm` 코드 일치 검사(라이브러리)는 그대로. 코드 재입력·`USER_TERMINAL_CODE_NOT_RETYPED`는 되살리지 않는다.
   - 공용 함수 `user_terminal_rejection()`에 넣거나 별도 작은 함수로 둔다(REUSE 우선). COWORK·AUTO_CORE 경로 불변.
3. **문서**: broker-snapshot-reconciliation.md Fallback, tools/dev_pipeline/README.md 11·44·70행, 보고서 문구를 "대화형 콘솔에서 직접 실행하고 Enter 한 번"으로 맞춘다. 한계 문단은 유지하되 "숨은 새 콘솔/의사 콘솔/키 입력 주입은 막지 못한다. 단, 새 콘솔 창은 Enter를 기다리며 멈추므로 키 입력을 주입해야 통과한다(재입력 때와 같은 강도)"로 정확히 쓴다. 앞 보고의 '새로 열리는 경로' 절은 이 수정으로 좁혀졌음을 갱신한다(삭제하지 말고 "수정 1 이후" 문장 추가).
4. **테스트**: 대화형 가정 + Enter(빈 문자열) → 통과, 아무 문자열 + Enter → 통과, 입력 끝(EOFError / ReadLine null) → 거절, 숨은 새 콘솔 흉내(핸들은 콘솔이고 입력이 끝) → 거절, 기존 NUL·파이프 거절 유지. dev-merge.ps1 정적 검사에 `ReadLine` 호출과 `$null` 처리, `-cne` 비교가 **없음**을 단언. 가능하면 이 PC에서 `Start-Process -WindowStyle Hidden`으로 숨은 콘솔에 `-ApproveAuthority`를 실행해 15초 안에 끝나지 않는지 **측정**해 보고에 적는다(읽기·측정만, 실제 병합 없음 — 없는 id `hnd-selftest`를 쓰고 끝나지 않으면 종료시킨다).
5. 테스트 기준선·이후 이름 목록과 보고서 갱신(바뀐 줄, 측정, 한계). 새 실패 0.

## 지킬 것
앞 지시문과 같다. 검사는 거절만 더한다. 우회 환경 변수·스위치 금지. 단언 약화 금지. 판단이 안 서면 BLOCKED.md. 커밋·병합 금지.

## Judge 추가 확인
J7 Enter 확인이 통과 조건을 넓히지 않는가(내용 비교 없음이 안전한 이유: 앞선 모든 검사는 그대로이고 이 단계는 거절만 더함). J8 숨은 새 콘솔 경로가 Enter 대기로 멈추는 코드 경로.
