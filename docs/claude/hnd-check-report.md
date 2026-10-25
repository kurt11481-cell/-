---
id: hnd-check-report
title: "hnd-check Builder 보고 — 승인류 스크립트에 '사람이 직접 친 대화형 터미널인가' 검사"
date: 2026-10-25
class: "권한·한도(K3) 수동 경로 Builder. worktree hnd-check(브랜치 worktree-hnd-check, base b2cd42e). 커밋·병합 없음"
source: "docs/claude/hnd-check-builder-prompt.md (메인 체크아웃, 미커밋 파일로 읽음)"
authority: "order_authority=false · quantity_authority 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음 · CLAUDE.md·AGENTS.md·.claude/ 무변경"
consumers: "독립 Judge(J1~J6) · 사장(병합 결정, 대화형 시험) · Cowork(남은 위험 3의 문서 갱신)"
---

# 결론
- `reconcile_broker_state.py apply`·`portfolio_review_journal.py apply`의 `--confirmed-via USER_TERMINAL`과 `tools/dev-merge.ps1 -ApproveAuthority`는 이제 **입력·출력이 콘솔인 실행에서, 코드(또는 id)를 한 번 더 손으로 쳐야** 통과한다. 파이프·리다이렉트·헤드리스 실행은 막힌다.
- `COWORK_CHAT_USER_MESSAGE` 경로, `AUTO_CORE` 경로(append_auto_core_entries·apply_auto_core), `-ApproveAuthority` 없는 일반 병합은 실행되는 줄이 바뀌지 않았다. 라이브러리 `apply_user_confirmed_broker_snapshot.py`는 한 바이트도 안 바뀌었다(sha256 6884b197… 전후 같음).
- 검사는 **거절만 더한다.** 통과한 뒤에는 기존 코드 일치·만료·해시·불변 조건 검사가 전부 그대로 돈다.
- 테스트: 기준선 대비 새 실패 0(알려진 PLTR 레지스트리 실패 1건만 그대로). 새 테스트 19개(새 파일 16 + test_dev_pipeline 3).

# 한계 (지시문 문단 그대로)
**같은 Windows 계정의 GUI 자동화(화면 조작 도구)로 진짜 콘솔에 타이핑하는 에이전트는 막지 못한다. 암호학적 증명이 아니라 파이프·헤드리스 경로 차단이다. 이 한계 때문에 CLAUDE.md의 절차 규칙("Claude Code·Codex·예약·Judge는 apply 금지")은 그대로 유지된다.**

이번에 확인한 같은 부류(역시 막지 못함):
- **의사 콘솔(ConPTY)**: Windows Terminal·VS Code 터미널·node-pty류처럼 의사 콘솔로 셸을 띄우는 도구는 프로그램 입장에서 진짜 콘솔이다(isatty·IsInputRedirected 모두 "콘솔"). 그런 도구를 쓰는 에이전트가 명령과 코드/id를 쳐 넣으면 통과한다. **Desktop Commander가 파이프인지 의사 콘솔인지는 확인 필요**(이 PC의 플러그인 폴더에서 소스를 찾지 못함). 파이프라면 STOP, 의사 콘솔이라면 통과.
- 숨은 콘솔에 `< CON > CON`으로 붙고 키 입력을 주입(WriteConsoleInput)하는 프로그램.
- 참고(막힘): Windows는 `NUL`을 터미널로 본다(이 PC Python 3.13.15에서 `< NUL > NUL` → isatty True/True 측정). 그래서 NUL은 isatty 단계는 지나가지만 재입력 단계에서 읽을 것이 없어(EOF) `USER_TERMINAL_CODE_NOT_RETYPED`로 막힌다(테스트 `test_the_code_is_typed_once_more`의 "" 경우, `test_console_apply_needs_the_same_code_again`의 None 경우).

# 검사 규칙 요약
1. **tools/dev-merge.ps1** — `-ApproveAuthority`가 있을 때만, id 형식 검사 바로 뒤(python 찾기·로그 폴더 만들기·devpipe 실행 전):
   - a. `[Console]::IsInputRedirected` 또는 `[Console]::IsOutputRedirected`가 참이거나 `$Host.Name -ne 'ConsoleHost'`이거나 `-not [Environment]::UserInteractive` → `DEV-MERGE <id> STOP_NOT_INTERACTIVE`, exit 2.
   - b. 화면(Write-Host, 출력 줄과 섞이지 않음)에 `권한 변경 병합입니다. 승인하려면 id '<id>'를 그대로 입력하세요: ` → `[Console]::ReadLine()`이 id와 대소문자까지 같지 않으면(`-cne`, 다듬기 없음, 입력 끝 $null 포함) `DEV-MERGE <id> STOP_ID_NOT_CONFIRMED`, exit 2.
   - 안내문은 파일이 ASCII 전용(머리 주석 규칙, PS 5.1이 BOM 없는 파일을 ANSI로 읽음)이라 `[regex]::Unescape` 유니코드 이스케이프로 넣었다. PS 5.1에서 만든 문자열이 지시문 문장과 정확히 같음을 측정했고(scratch 시험), 정적 테스트가 이스케이프를 풀어 같은 문장인지 매번 확인한다.
   - 스위치가 없으면 새 블록은 `if ($ApproveAuthority)` 밖이라 실행되지 않는다. 종료 코드 0/2/3, 출력 첫 줄 형식 그대로. 새 param·환경 변수·테스트 분기 없음(정적 테스트로 고정).
2. **reconcile_broker_state.py `cmd_apply`·portfolio_review_journal.py `cmd_apply`** — `--confirmed-via USER_TERMINAL`일 때만, 제안 파일을 읽기 전:
   - a. `sys.stdin.isatty()`와 `sys.stdout.isatty()`가 둘 다 `True`여야 한다(`is True`; 스트림 없음·닫힘·이상한 값도 비대화형). 아니면 reconcile은 로케일 새 키 `apply_terminal_not_interactive` 한 줄, journal은 기존 형식 `기록하지 않았습니다: USER_TERMINAL_NOT_INTERACTIVE`, 반환 2.
   - b. `input()`으로 코드를 한 번 더 받는다(reconcile 안내 `확인 코드를 한 번 더 입력하세요: `, journal 안내 `Type the confirmation code again: `). 양쪽 strip·upper로 `--confirm`과 다르거나 입력 끝이면 `USER_TERMINAL_CODE_NOT_RETYPED`로 거절(reconcile은 기존 `apply_rejected` 형식, journal은 `journal_apply_rejected` 형식), 반환 2.
   - c. 통과하면 기존 흐름 그대로. 재입력은 코드 검사를 대신하지 않는다(`--confirm 00000000` + 재입력 `00000000` → 라이브러리의 `CONFIRM_CODE_MISMATCH`, 테스트 `test_retyping_never_replaces_the_code_check`).
   - 공용 함수 1개: `portfolio_review_journal.user_terminal_rejection`(802~820행). 반환 None = 통과, 아니면 거절 사유 코드.

## 공용 함수 위치를 journal로 둔 이유 (지시문 2번 "보고에 이유")
- 순환 import는 어느 쪽에도 없다(import 그래프를 ast로 계산: apply 모듈 최상단은 cash_flow_evidence·kiwoom_broker_shadow·validation_common만, 그 셋은 journal을 import하지 않음).
- 그래도 journal에 둔 것: ① reconcile → journal 의존은 이미 있다(`reconcile_broker_state.py:403-404`의 cmd_auto 지연 import, 변경 전 393-394행) → 새 모듈 의존 0. ② apply 모듈에 두면 journal이 상태 쓰기 라이브러리를 새로 import하게 된다(journal은 지금도 `CONFIRMATION_METHODS`를 import하지 않고 따로 둔다, 67행; 모듈 설명 "never touches portfolio state"). ③ `apply_user_confirmed_broker_snapshot.py`를 한 바이트도 안 바꿔 K3 검토 면적이 준다. ④ 테스트 patch 대상이 하나(`portfolio_review_journal.user_terminal_rejection`)로 두 CLI를 같이 덮는다.
- reconcile은 USER_TERMINAL 분기 안에서만 지연 import한다 → COWORK·propose·show·auto 경로의 import·실행은 그대로.
- 경계 테스트 `test_analysis_path_never_reaches_the_apply_modules`(분석 경로가 apply 모듈에 닿지 않음)는 그대로 통과(journal이 apply 모듈을 import하지 않으므로 영향 없음).

## journal 재입력 안내만 영어인 이유
- `scripts/*.py`는 ASCII만 허용된다(`test_language_contract.py:20-22`, `test_decision_journal_cards.py:776-780`). journal 메시지 파일(`assets/locales/portfolio-exposure-ko-KR.json`)은 허용 목록 밖이다. 그래서 정본 영어 문구를 상수로 두고(71행), reconcile은 자기 로케일의 한국어 안내를 넘긴다. 다음 일반 변경에서 journal 로케일 키로 옮길 수 있다.

# 바뀐 줄 (파일:행, 변경 후 기준)
| 파일 | 행 | 내용 |
|---|---|---|
| tools/dev-merge.ps1 | 4 | Usage 머리 주석 1줄 |
| tools/dev-merge.ps1 | 38-56 | `if ($ApproveAuthority) { … }` 검사 블록(신규). 그 밖의 줄 무변경 |
| manage-us-stock-strategy/scripts/portfolio_review_journal.py | 17-18 | 모듈 설명(apply 줄) |
| 〃 | 68-71 | 상수 3개 + 주석 |
| 〃 | 802-820 | `user_terminal_rejection()` 신규 |
| 〃 | 826-829 | `cmd_apply` USER_TERMINAL 분기(제안 읽기 전) |
| manage-us-stock-strategy/scripts/reconcile_broker_state.py | 8-10 | 모듈 설명(apply 줄) |
| 〃 | 286-294 | `cmd_apply` USER_TERMINAL 분기(제안 읽기 전) |
| manage-us-stock-strategy/assets/locales/reconcile-broker-state-ko-KR.json | 51-53 | 51행 끝 쉼표, 새 키 `apply_terminal_not_interactive`·`apply_terminal_retype`. **메시지 목록 파일**: reconcile의 `_messages()`가 읽는 `LOCALE_PATH`(reconcile_broker_state.py:42) — 기존 거절 문구가 모두 여기 있어 REUSE |
| manage-us-stock-strategy/references/broker-snapshot-reconciliation.md | 180-183 | 3절 Fallback 뒤 2문장 |
| tools/dev_pipeline/README.md | 11, 44, 70 | 11·70: authority 병합은 사장이 대화형 PowerShell 창에서 실행 + id 재입력("이 대화의 사장 결정" 문구는 유지 — dcdev-claudemd-report.md:19의 이전 Judge 지적). 44: 수동 경로 병합 스크립트도 같은 검사를 넣는다 1문장 |
| manage-us-stock-strategy/tests/test_reconcile_broker_state.py | 757-761 | `CliTests.setUp`에 검사 patch(통과) 1개 — mock 추가만 |
| manage-us-stock-strategy/tests/test_portfolio_review_journal.py | 15, 227-230 | `mock` import, 기존 호출을 patch `with` 안으로(단언 그대로) |
| manage-us-stock-strategy/tests/test_decision_journal_cards.py | 290-293 | 기존 호출·단언을 patch `with` 안으로 들여쓰기만 |
| manage-us-stock-strategy/tests/test_dev_pipeline.py | 1296-1321 | 정적 검사 `test_merge_authority_needs_an_interactive_console` |
| 〃 | 1492-1558 | 복사본 실행 `MergeCopyConsoleTests`(2개) + 가짜 devpipe |
| manage-us-stock-strategy/tests/test_approval_human_check.py | 1-250 | 새 파일(16개) |
| docs/claude/hnd-check-report.md | 전체 | 이 보고 |

모든 파일 CRLF 유지(바뀐 파일 전부 bare LF 0 측정), `.py`·`.ps1`은 ASCII 유지. 허용 목록 밖 파일 변경 0.

# 테스트
명령 형식: `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"`(auto_core는 `-p "test_auto_core*"`).

| 패턴 | 기준선(수정 전, HEAD b2cd42e, 깨끗한 worktree) | 이후 |
|---|---|---|
| test_reconcile_broker_state* | Ran 56, OK | Ran 56, OK |
| test_portfolio_review_journal* | Ran 14, OK | Ran 14, OK |
| test_decision_journal_cards* | Ran 36, OK | Ran 36, OK |
| test_dev_pipeline* | Ran 120, OK | Ran 123, OK |
| test_auto_core* | Ran 529, FAILED (failures=1, skipped=1) | Ran 529, FAILED (failures=1, skipped=1) |
| test_approval_human_check* | (없음) | Ran 16, OK |

- 기준선 실패·오류 이름: FAIL `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='PLTR')` 1건(알려진 PLTR 레지스트리). ERROR 0.
- 이후 실패·오류 이름: 위와 같은 1건뿐. ERROR 0. **새 실패 0.**
- 추가: `test_language_contract*` Ran 2 OK(scripts/*.py ASCII), 스키마 감사 `validate_schema_contracts.py` PASS(errors []).
- 전체 스위트(`-p "test*.py"`, test-runner, 변경 후 최종본): Ran 3338, FAILED (failures=22, errors=9, skipped=3). 지시문 대상 5개 패턴과 새 파일은 이 실패 목록에 없다. 31건의 출처를 따로 확인했다(전체 스위트의 변경 전 기준선은 재지 않았으므로 아래 방법):
  - 실패가 난 14개 모듈(PLTR의 test_auto_core_decide 제외)을 HEAD 사본(`git archive HEAD`, scratch)과 변경 후 worktree에서 각각 돌려 비교: 변경 후 실패 30건 중 28건은 HEAD 사본에서도 같은 이름으로 실패(사본은 무시 파일이 없어 실패가 더 많다: 오류 줄 248 대 72).
  - 나머지 2건(`test_evaluate_timing_integration`의 `test_i0b_t1_timing_position_left_in_policy_still_fails_on_anchor_mismatch`, `test_technical_validation_failure_does_not_hide_hard_risk`)은 HEAD 사본에서 ERROR(상태 파일 `stock-strategy-system/portfolio_state.json` 없음), worktree에서 FAIL(복사된 실제 상태 값과 단언 불일치). 이 테스트가 불러오는 `evaluate_alerts.py`·`validate_technical_snapshot.py`의 import 그래프에는 바뀐 모듈이 없고 상태 파일은 손대지 않았다 → 이 변경과 무관. 같은 상태 파일로 HEAD 사본을 다시 돌리는 시험은 상태 파일 복사가 권한에서 거부돼 하지 않았다(확인 필요로 남김: 사장 PC 메인 체크아웃에서 같은 모듈을 돌리면 같은 2건이 나오는지).
  - 나머지 오류 9건은 worktree에 없는 workspace/·stock-strategy-system/ 자료(FileNotFoundError), v2_6_7 실패 14건은 같은 원인(현재 Acceptance 연결이 가리키는 manifest 없음), 스케줄 프롬프트 1건은 `docs/claude/scheduled-prompts/pending-cardreuse/diff-v3.2-v3.3.txt`.
- 기존 테스트 처리(J5): 단언 변경·삭제·skip 0. `CliTests.setUp` patch 1개로 클래스 안 USER_TERMINAL 테스트(지시문의 828·861·868·905행 근처) 기존 의미 유지. 817·876행 근처 두 테스트는 argparse가 `cmd_apply` 전에 거절(SystemExit 2)해 검사에 닿지 않는다. journal 227행·cards 291행은 patch `with`만 추가.
- 검사 끄기 시험(scratch, 소스 무변경): `user_terminal_rejection`을 항상 통과로 바꿔 새 파일을 돌리면 거절 테스트 16건이 실패한다 → 새 테스트가 검사를 실제로 붙잡는다.
- dev-merge.ps1: 정적 검사 1개(블록 위치·네 조건·두 STOP 줄·`ReadLine -cne $Id`·안내문 디코드 일치·param은 Id·ApproveAuthority뿐·`$env:`는 기존 ComSpec·SystemRoot뿐) + 복사본 실행 2개. 복사본 실행은 `test_journal_score_runner.py:83-114`의 방식 REUSE: 임시 폴더에 복사한 dev-merge.ps1과 가짜 devpipe.py만 돈다(저장소의 dev-merge.ps1·devpipe.py는 실행 안 함, git 없음, 경로가 저장소 밖인지 단언). 결과: 스위치 없음 → 기존 결과(가짜 0 → `DEV-MERGE demo MERGED` exit 0, 가짜 3 → `NEEDS_APPROVAL` exit 3, devpipe 인자 `merge --repo <임시> --id demo` 그대로). 스위치 + 입력 없음, 스위치 + 파이프로 올바른 id → 둘 다 `DEV-MERGE demo STOP_NOT_INTERACTIVE` exit 2, devpipe 호출 0, 로그 폴더 생성 0. 이 두 클래스는 Windows PowerShell이 없으면 skip(같은 선례); 이 PC에서는 실행됨(skip 수 변화 0).
- **대화형 성공 경로는 사람 시험 필요**(아래 절차). 자동 시험은 가짜 스트림(isatty True인 StringIO)으로 Python 쪽 성공·불일치 경로만 덮는다.

# 검토 순서
- **NO_CHANGE**: 해당 없음 — 지시문이 막으려는 경로(파이프·헤드리스 USER_TERMINAL apply, 에이전트의 -ApproveAuthority)는 변경 전 코드에 검사가 0건이었다(approval-without-cowork-review-2026-10-25.md 사실 1, 이 세션 grep: scripts에 isatty·input 0건).
- **REMOVE/SIMPLIFY**: 지울 것 없음. 검사는 입구 세 곳에만, 라이브러리(`apply_confirmed`·`apply_proposal_entries`·`append_auto_core_entries`)는 무변경. 두 CLI가 같은 함수 1개를 쓴다.
- **REUSE**: 공용 함수 1개(journal), 기존 거절 형식(`apply_rejected`·`journal_apply_rejected`), 기존 로케일 파일, 기존 복사본 실행 시험 방식, 기존 픽스처(test_reconcile_broker_state의 base_state·account_results·TempStateCase, test_portfolio_review_journal의 not_activated_review).
- **REPLACE**: 없음.
- **ADD**: 검사 블록 3곳, 로케일 키 2개, 문서 줄(reference 2문장, README 3줄), 테스트.
- **검사를 dev-merge.ps1과 두 CLI에만 두는 것으로 충분한가**: 스크립트가 승인을 검증하는 경로는 이 셋뿐이다(approval-without-cowork-review 사실 3). 정책·상태 변경, decision_mode "켜" 등은 스크립트 검사가 없는 구조라 이번 범위로 덮을 수 없다(그대로 절차 규칙). 수동 경로 병합 스크립트는 git을 직접 써서 dev-merge 검사를 거치지 않으므로 README 44행 규칙으로만 덮인다(남은 위험 2).
- **개별 병합 스크립트 13개는 건드리지 않는 것이 맞는가**: 맞다. `docs/claude/*merge*.ps1` 13개(메인 체크아웃 기준; 이 worktree에는 11개 커밋, recon-dt·cf-b2n은 메인에 미커밋) 모두 대화형 검사가 없지만(grep 0건), 각각 고정된 base SHA·sha256로 이미 실행된 기록이다(예: close-confirm-e-merge-2026-10-21.ps1:16 base, 20행부터 파일별 sha256). 다시 돌릴 대상이 아니고, 고치면 기록 바이트가 바뀐다. 그중 2개(merge-cmpfix2-ust21100-2026-10-13.ps1:37, merge-ust21100-fix2-2026-10-13.ps1:37)는 같은 프로세스 안에서 `dev-merge.ps1 … -ApproveAuthority`를 부르므로, 다시 실행되더라도 새 검사가 그대로 걸린다.

# 남은 위험
1. 의사 콘솔·GUI 자동화·숨은 콘솔 주입은 못 막는다(위 한계). 바뀔 조건: Desktop Commander가 의사 콘솔로 셸을 띄운다는 사실이 확인되면, Cowork 경로도 기술적으로는 통과 가능 → 절차 규칙이 유일한 방어임을 다시 명시해야 한다.
2. 수동 경로 병합 스크립트(`docs/claude/<id>-merge-*.ps1`)는 코드로 강제되지 않는다(README 규칙만). 강제하려면 공용 검사 조각 파일이 필요한데, 이번 지시문은 새 .ps1을 금지해 만들지 않았다.
3. Cowork 문서가 "Cowork가 -ApproveAuthority로 병합"이라고 적은 곳: `docs/claude/dc-dev-2026-10-22.md:38`(메인 체크아웃의 미커밋 파일, 허용 목록 밖, 손대지 않음). 이제 그 실행은 (파이프라면) `STOP_NOT_INTERACTIVE`. Cowork가 갱신할 후보. CLAUDE.md:55·61은 "Cowork never with -ApproveAuthority"와 "사용자 결정 뒤"라 이번 변경과 충돌하지 않는다 → CLAUDE.md 수정 불필요, BLOCKED 아님.
4. 사장 손: 권한 병합 1건당 PowerShell 창에서 명령 1줄 + id 1줄(이전 dc-dev Q2 a에서는 Cowork 대화 결정 문장으로 Cowork가 병합할 수 있었다). 주간 일상 손은 0 그대로(권한 병합은 일상 작업이 아님). USER_TERMINAL apply는 코드 1줄 추가. 지시문 frontmatter "승인 1건당 터미널 입력은 지금과 같거나 id 재입력 1줄 추가"와 같다.
5. 창 종류: Git Bash(mintty)는 Python에 콘솔이 아니어서(파이프) USER_TERMINAL apply가 늘 STOP. PowerShell ISE·VS Code PowerShell 확장 창은 `$Host.Name`이 ConsoleHost가 아니어서 dev-merge가 STOP. 일반 "Windows PowerShell" 창(Windows Terminal 안의 PowerShell 포함)을 쓴다.
6. 재입력은 Enter까지 기다린다(시간 제한 없음). 대화형 창에서만 생기고 비대화형은 즉시 STOP이라 자동 작업을 막지 않는다.
7. 새 테스트 중 복사본 실행 2개는 powershell.exe를 띄운다(각 1초 안팎). Windows가 아닌 곳에서는 skip.

# 사람이 한 번 해 볼 대화형 시험 절차 (병합 뒤, 1회, 선택)
모두 **없는 id·없는 제안 파일**을 써서 상태·일지·병합이 바뀔 수 없다. 창: 시작 메뉴 → **Windows PowerShell**(ISE 아님). 먼저 `cd "E:\사업\##금동한\코덱스저장소"`.

A. dev-merge 권한 병합 검사
1. `.\tools\dev-merge.ps1 hnd-selftest -ApproveAuthority` → 화면에 `권한 변경 병합입니다. 승인하려면 id 'hnd-selftest'를 그대로 입력하세요: ` → `HND-SELFTEST`(대문자)를 치고 Enter → `DEV-MERGE hnd-selftest STOP_ID_NOT_CONFIRMED`. 이어서 `$LASTEXITCODE` → `2`.
2. 같은 명령 → 이번에는 `hnd-selftest`를 정확히 입력 → 검사를 지나 devpipe가 `DEV-MERGE hnd-selftest STOP_NO_RESULT reason=result.json`(그런 run이 없음, devpipe.py:2034-2035). 병합 없음. `workspace\outputs\dev-runs\_merge\` 아래 로그 폴더 1개만 생긴다(git 무시 폴더).
3. 비대화형 확인: `"hnd-selftest" | powershell -NoProfile -File .\tools\dev-merge.ps1 hnd-selftest -ApproveAuthority` → 안내문 없이 `DEV-MERGE hnd-selftest STOP_NOT_INTERACTIVE`.

B. 대조 apply(USER_TERMINAL) 검사
1. `python manage-us-stock-strategy/scripts/reconcile_broker_state.py apply --confirm TESTONLY --confirmed-via USER_TERMINAL --proposal C:\no-such-folder\x.json` → `확인 코드를 한 번 더 입력하세요: ` → `WRONG` → `적용하지 않았습니다: USER_TERMINAL_CODE_NOT_RETYPED`(제안 파일을 읽기 전).
2. 같은 명령에 `testonly` 입력 → 검사를 지나 `적용하지 않았습니다: …`(없는 제안 파일 오류). 상태 변화 없음.
3. 비대화형: `"TESTONLY" | python manage-us-stock-strategy/scripts/reconcile_broker_state.py apply --confirm TESTONLY --confirmed-via USER_TERMINAL --proposal C:\no-such-folder\x.json` → `적용하지 않았습니다: 사장 터미널에서 직접 실행해야 합니다(대화형 콘솔 아님 — …)`.

C. 일지 apply(USER_TERMINAL) 검사
1. `python manage-us-stock-strategy/scripts/portfolio_review_journal.py apply --proposal C:\no-such-folder\p.json --confirm TESTONLY --confirmed-via USER_TERMINAL --journal C:\no-such-folder\j.json` → `Type the confirmation code again: ` → `WRONG` → `기록하지 않았습니다: USER_TERMINAL_CODE_NOT_RETYPED`.
2. 비대화형: 앞에 `"TESTONLY" | `를 붙여 같은 명령 → `기록하지 않았습니다: USER_TERMINAL_NOT_INTERACTIVE`.

(선택, 확인 필요 해소용) Desktop Commander가 파이프인지 보려면 Cowork가 A-3과 같은 형태로 없는 id를 비대화형으로 한 번 실행해 `STOP_NOT_INTERACTIVE`가 나오는지 보면 된다. 단 Cowork의 `-ApproveAuthority` 사용은 CLAUDE.md:55가 금지하므로 사장 결정이 있을 때만.

# 지킨 것 (J1~J6 대응)
- 실행하지 않은 것: auto_core.py, reconcile/journal apply(실제 상태·일지 대상), dev-run·dev-merge·dev-queue(저장소의 dev-merge.ps1은 실행 안 함 — 테스트가 임시 폴더 복사본만 돌림), 키움·kiwoomcli 없음, 비밀 파일 읽기 없음, git add·commit·push·브랜치 변경 없음.
- 변경은 허용 목록 안 파일뿐, 커밋하지 않은 채 worktree에 있다.
