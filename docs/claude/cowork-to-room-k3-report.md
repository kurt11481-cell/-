---
id: cowork-to-room-k3-report
title: "cowork-to-room-k3 Builder 보고서 (R1~R4)"
date: 2026-11-20
class: "K3 수동 경로 Builder 결과. Judge 판정 전 — 병합 안 됨"
source: "docs/claude/cowork-to-room-k3-proposal-2026-11-20.md(2판) · docs/claude/cowork-to-room-k3-builder-prompt.md · 코디네이터 추가 요구 4건(Judge 지시문 docs/claude/cowork-to-room-k3-judge-prompt.md 기준)"
authority: "order_authority=false · quantity_authority 변경 없음 · 키움 호출 0 · 실제 상태·일지·원장·백업·정책 쓰기 0 · .claude 변경 0"
---

# 0. 결론

R1~R4를 수정안 2-1·2-2절대로 구현했다. 새 시험 T1~T20 전부 PASS, 기존 시험 새 실패 0(기준선과 같은 2건만 실패, 둘 다 이 변경과 무관).
Judge는 이 보고서가 아니라 브랜치 머리 커밋을 판정한다. 병합 전까지 현행 규칙 그대로다.

```
R1 대조 apply ── 스레드 직접 입력 '확인 <코드>' → PROJECT_THREAD_USER_DECISION(4칸, 코드는 4번째 칸)
  │
  ▼
R2 일지 ── 카드 2종 + line_review_completed·peak_review_card_completed(직접 입력·4번째 칸 코드), s5_activation 제외
  │
  ▼
R3 propose ── 일지에 S5 활성 + 증거 없음 → 키움 조회 전 거부 (CORRUPT·읽기 오류도 거부)
  │
  ▼
R4 CLAUDE.md·참조 문서 ── 수동 대조 = 자동 코어 HOLD의 공식 탈출구(증거·기록일 조건)
```

# 1. 바뀐 줄 (파일:행, 브랜치 머리 기준)

| 파일 | 행 | 내용 |
|---|---|---|
| CLAUDE.md | 25~40 | R1 스레드 예외(직접 입력만·카드 탭 제외·4칸·바로 앞 제안·같은 날·1회·확인 아닌 것 목록·PROJECT_THREAD만·Windows 파이썬만·다른 세션 금지) + R4 탈출구. "never type or guess the code or reuse one", "Before applying, read …" 유지 |
| CLAUDE.md | 52~56 | R2: 스레드 허용 = 카드 2종 + S5 두 종류(직접 입력·4번째 칸 코드), s5_activation 금지, PROJECT_THREAD만, Windows 파이썬만 |
| CLAUDE.md | 132 | Decision journal 문장 끝에 L4·L5·고점 검토 한 문장 |
| scripts/validation_common.py | 44~63 | `PROJECT_THREAD_METHOD`, `project_thread_message_valid`(옮김, 규칙 동일), `project_thread_code_in_verbatim`(`split("|", 3)[3]`에서만 대문자 비교) |
| scripts/apply_user_confirmed_broker_snapshot.py | 17~20, 32~35, 284~293 | 공용 함수 import, CONFIRMATION_METHODS에 새 방법, 키움 분기에서 PROJECT_THREAD면 형식(`PROJECT_THREAD_MESSAGE_INVALID`)·4번째 칸 코드(`CONFIRM_CODE_NOT_IN_USER_MESSAGE`) 검사. COWORK·USER_TERMINAL 줄은 그대로 elif로 |
| scripts/reconcile_broker_state.py | 1~22 | 머리말(R3, 스레드 방법) |
| 같은 파일 | 42 | PROJECT_THREAD_METHOD import |
| 같은 파일 | 282~291 | cmd_propose: 키움 reader 호출 전 R3 판정, 거부 시 종료 2(출력 폴더·상태 불변) |
| 같은 파일 | 344~365 | `activation_evidence_rejection`: load_journal 상태와 journal_view 상태 **둘 다** 검사(MISSING = 활성 없음, 그 밖 = 거부), 읽기 예외 = `DECISION_JOURNAL_UNREADABLE` |
| 같은 파일 | 387~389, 401~403 | user_message 필수 = COWORK·PROJECT_THREAD, 코드 대체는 USER_TERMINAL만 |
| 같은 파일 | 559~560, 569~572 | propose `--journal`(기본값 = auto 584행과 같음), apply `--user-message` help |
| scripts/portfolio_review_journal.py | 15~25 | 머리말: '(no code)'를 카드 항목 한정으로 고치고 새 두 종류 규칙·Windows 파이썬 한정 |
| 같은 파일 | 54~57, 79~84 | 공용 함수 import, `PROJECT_THREAD_CODE_ENTRY_TYPES`(2종)·`PROJECT_THREAD_ENTRY_TYPES`(명시 4종) |
| 같은 파일 | 198~205 | 체인 재검사: 허용 4종, 새 두 종류 4번째 칸 코드 |
| 같은 파일 | 254~259 | `project_thread_message_valid` 이름·동작 유지, 본체는 validation_common 호출 |
| 같은 파일 | 569~576 | apply: 같은 검사 |
| schemas/portfolio-review-journal.schema.json | 4 | description만(enum 29행 불변) |
| assets/locales/reconcile-broker-state-ko-KR.json | 5, 6, 39, 52 | 사장실 스레드 문구, 새 키 `propose_cash_flow_evidence_required`(normalize 명령 안내), 원문 필요 문구 |
| references/broker-snapshot-reconciliation.md | 155~214 | 2a절 스레드 갈래, '코드는 사람 증명 아님' 단락 확장, deny·훅 사실 정정(확인 필요 표기), Windows 파이썬 한정 |
| 같은 파일 | 235~272 | 4절: 활성 뒤 필수(R3), `--journal`을 넘기지 않는다는 규칙, 활성 전만 "as before", R4 탈출구 |
| references/portfolio-exposure-review.md | 335~341 | 스레드 기록 가능 문장 |
| tests/test_cowork_to_room_k3.py | 새 파일 | T1~T20 (아래 3절) |

# 2. 기존 시험 변경 (단언 변경은 1곳뿐)

| 파일:행 | 변경 | 이유 |
|---|---|---|
| test_auto_core.py 1056~1062 | 기대 튜플 2곳에 PROJECT_THREAD_USER_DECISION 추가 | 수정안 2-2 표(안 고치면 반드시 실패). 유일한 단언 변경 |
| test_reconcile_broker_state.py 851~852 (propose 도우미), 890~891, 955 | 임시 `--journal`(없는 임시 경로 = MISSING) 인자 추가 | 기본 일지(.gitignore 대상, worktree엔 없음)에 기대지 않게. 단언 변경 아님 |
| test_approval_human_check.py 269~271 | 같음 | 같음 |
| test_cash_flow_evidence.py 315~316 | 같음 | 같음(코디네이터 추가 요구 (1)로 허용 파일에 들어옴) |

`git diff 22d44cf -- manage-us-stock-strategy/tests`의 삭제 줄은 위 튜플 2줄과 propose 호출 인자 줄뿐이고, 지워진 assert는 튜플 2줄(새 값으로 다시 단언)뿐이다. tests 안 `"propose"` 호출 5곳(test_approval_human_check 266, test_cash_flow_evidence 312, test_reconcile_broker_state 848·886·952)과 새 파일의 호출(CliCase.propose)은 모두 임시 `--journal`을 넘긴다.

# 3. 시험 결과

## 3-1. 새 시험 (tests/test_cowork_to_room_k3.py, 33개 전부 PASS, 건너뜀 0)

| T | 시험 이름 |
|---|---|
| T1 | ReconcileThreadLibraryTests.test_t1_thread_apply_records_method_and_four_fields · test_t1_lower_case_code_in_verbatim_field_is_accepted_like_the_other_methods · ThreadCliTests.test_t1_cli_apply_with_thread_fields |
| T2 | ReconcileThreadLibraryTests.test_t2_thread_without_message_is_rejected_by_the_library · ThreadCliTests.test_t2_cli_thread_without_user_message_is_rejected |
| T3 | ReconcileThreadLibraryTests.test_t3_bad_four_field_format_is_rejected_by_the_library(라이브러리 직접, 앞 칸 `|` 밀기 포함) · ThreadCliTests.test_t3_cli_bad_format_is_rejected |
| T4 | ReconcileThreadLibraryTests.test_t4_four_fields_without_this_code_are_rejected |
| T5 | ReconcileThreadLibraryTests.test_t5_cowork_and_terminal_paths_are_unchanged · test_t5_cowork_message_with_the_code_still_applies (+ 기존 시험 파일 전부 통과) |
| T6 | JournalThreadTests.test_t6_line_and_peak_review_from_the_thread_are_recorded_and_verify |
| T7 | JournalThreadTests.test_t7_s5_review_entries_need_the_code_in_the_verbatim_field · test_t7_hand_edited_s5_review_entry_without_code_is_caught_by_verify |
| T8 | JournalThreadTests.test_t8_s5_activation_is_never_a_thread_entry(apply·verify 둘 다) · test_t8_allowed_thread_types_are_an_explicit_list_of_four |
| T9 | JournalThreadTests.test_t9_card_entries_from_the_thread_still_need_no_code |
| T10 | ProposeEvidenceTests.test_t10_activation_without_evidence_is_refused_before_any_read(reader 0회, 출력 폴더 없음, 상태 바이트 불변) |
| T11 | ProposeEvidenceTests.test_t11_journal_without_activation_proposes_as_before |
| T12 | ProposeEvidenceTests.test_t12_corrupt_or_unreadable_journal_is_refused_before_any_read · test_t12_journal_view_corrupt_is_refused_even_when_load_journal_is_ok(MULTIPLE_S5_ACTIVATION_ENTRIES·S5_ACTIVATION_ENTRY_INVALID — 추가 요구 (3)) · test_t12_read_error_is_refused_before_any_read |
| T13 | ProposeEvidenceTests.test_t13_activation_with_evidence_proposes_as_before |
| T14 | AutoPathUnchangedTests.test_t14_auto_functions_are_unchanged_and_never_call_the_r3_check(reconcile_auto·cmd_auto 등 5개 함수 소스가 22d44cf와 바이트 동일) · test_t14_propose_journal_default_is_the_auto_default |
| T15 | ReconcileThreadLibraryTests.test_t15_code_only_in_the_id_account_or_time_field_is_rejected · JournalThreadTests.test_t15_code_only_in_the_id_or_account_field_is_rejected |
| T16 | ReconcileThreadLibraryTests.test_t16_four_field_message_under_the_cowork_method_still_passes(현행 통과를 기록) |
| T17 | JournalThreadTests.test_t17_thread_review_entries_keep_the_activation |
| T18 | ProposeEvidenceTests.test_t18_missing_journal_proposes_as_before(조회 1회) |
| T19 | ReconcileThreadLibraryTests.test_t19_forged_but_well_formed_fields_pass_the_script(통과를 명시) |
| T20 | ReconcileThreadLibraryTests.test_t20_expired_proposal_is_rejected_even_with_valid_fields(BROKER_PROPOSAL_EXPIRED) |
| 공용 | SharedHelperTests.test_one_definition_is_shared_by_reconciliation_and_journal(같은 함수 객체, apply 모듈이 일지 모듈 import 안 함) · test_verbatim_field_rule |

거부 시험은 모두 사유 문자열까지 단언한다(assertRaisesRegex 또는 출력 포함 검사).

## 3-2. 대상 파일 (변경 뒤)
test_reconcile_broker_state 57 OK · test_approval_human_check 28 OK · test_cash_flow_evidence 19 OK · test_portfolio_review_journal 22 OK · test_decision_journal_cards 36 OK · test_run_portfolio_exposure_review 24 OK · test_portfolio_exposure_judge_fixes 29 OK · `-p "test_auto_core*"` 667개 중 실패 1(test_auto_core_decide RegistryTests SOXL — 기준선과 같음).

## 3-3. 전체 (`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"`)
- 기준선(22d44cf, 같은 worktree): Ran 3786, FAILED (failures=2, skipped=3)
  - test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='SOXL')
  - test_test_only_scheduler_control_plane.TestOnlySchedulerControlPlaneTests.test_os_diagnostic_d_uses_harmless_launcher
- 변경 뒤(코드 커밋 693719b와 같은 트리): Ran 3819(+33 새 시험), FAILED (failures=2, skipped=3) — 실패 이름 집합이 기준선과 같음(위 2건)
- 새로 실패한 시험 이름: 0. 기준선 측정은 편집 시작 전에 시작했다(시험 모듈은 시작 때 import됨). 정확한 대조는 Judge가 깨끗한 트리에서 다시 잰다.

# 4. 수정안 9절 확인 필요 (그대로 옮김 + Builder 확인 결과)
1. 회사PC VM 파이썬으로 portfolio_state.json·decision_journal.json을 쓸 때 Windows 실행과 바이트가 같은지(S7b 실사용 1건이 어느 셸이었는지 포함) — **확인 필요(이 Builder는 VM 셸이 없음, 시험 안 함)**. 그래서 코디네이터 추가 요구 (2)대로 CLAUDE.md 37~38·55~56행과 참조 문서 2a절에 "사장실 스레드는 reconcile apply·journal apply를 회사PC Windows 파이썬(Desktop Commander)으로만, VM 셸(device_bash)로는 안 함"을 넣었다. 같은 문장에 "Desktop Commander로 돌려도 방법은 PROJECT_THREAD_USER_DECISION이지 USER_TERMINAL이 아님"을 적어 J6 문장과 충돌하지 않게 했다.
2. 프로젝트 스레드에서 `.claude/settings.json` deny·훅이 발동하지 않는다는 것의 직접 시험 — **확인 필요**. 참조 문서는 단정하지 않고 '확인 필요'로 적었다. 새 사실 1건: 이 Builder 세션(Claude Code Bash 도구)에서 PreToolUse 훅 `kiwoom_order_block.py`가 `--confirm`이 든 명령을 실제로 거부했다(23행 패턴 `--confirm(?![A-Za-z0-9_-])`, 출력 "order marker '--confirm'"). 훅 매처는 device_bash·start_process·interact_with_process도 포함하므로(settings.json 46행), **훅이 스레드에서 발동하면 스레드의 `reconcile_broker_state.py apply --confirm …`과 `portfolio_review_journal.py apply --confirm …`은 셸 도구에서 거부된다**(안전 쪽 실패, 쓰기 0). 이 경우 R1·R2는 문서로는 허용돼도 실제로는 못 쓰며, 기존 S7b 일지 예외도 같은 영향을 받는다. 첫 실사용(수정안 7절 5단계) 때 확인해야 한다. 이 K3 범위에서 `.claude/**`·CLI 인자 이름은 바꾸지 않았다.
3. L4·L5 닫기 propose의 실제 입력 인자와 사장 결정 문장 형식 — 기존 시험·참조 문서에서 확인: `propose-line-review --review <review file> --line-id L2 --conclusion continue`, `propose-peak-review --review <review file> --symbol SOXL`(portfolio-exposure-review.md 326~327행, test_portfolio_review_journal.py 142~186행). 사장 결정 문장은 4번째 칸에 그 제안의 `확인 <코드>`가 들어간 직접 입력.
4. USER_TERMINAL이 Desktop Commander 대화형 프로세스로 콘솔 검사를 통과할 수 있는지 — **확인 필요(시험 안 함)**. 문서 규칙으로 스레드는 USER_TERMINAL을 쓰지 않는다.

# 5. 남은 위험
- 스크립트는 누가 4칸을 쳤는지, 어느 세션이 방법을 골랐는지 모른다(T16·T19로 기록). 사람 증명은 하네스 표시와 CLAUDE.md 규칙뿐(수정안 3절).
- 카드 탭과 직접 입력을 스크립트가 구별하지 못한다. 대조·S5 두 종류의 '탭 제외'는 문서 규칙과 4번째 칸 코드 요구(탭 선택지 이름에 코드가 들어가면 통과할 수 있음)로만 막힌다.
- R3 우회: `--journal`에 없는 경로를 넘기면 MISSING = 활성 없음으로 제안이 만들어진다. 제안·show에 일지 경로는 드러나지 않는다. 문서 규칙("Cowork와 스레드는 propose에 `--journal`을 넘기지 않는다", 참조 문서 4절)만 있다.
- R3로 키움 거래내역 저장이 안 되는 날엔 수동 대조 불가 → HOLD 유지(fail closed, 수정안 8절 바뀔 조건).
- 위 4-2의 훅 발동 시 스레드 apply 불가.
- 병합 뒤 사장이 프로젝트 지침 3·4절을 고쳐야 스레드가 실행한다(수정안 2-3절). 지침 3절 문장에도 "Windows 파이썬(Desktop Commander)으로만" 한정을 같이 넣어야 한다.

# 6. 하지 않은 것
주문·키움 도구 호출, reconcile propose·apply·auto 실행, 일지 apply(시험 안 임시 폴더 제외), auto_core.py 실행, .env·토큰·계좌번호 읽기, 실제 상태·원장·일지·백업·정책 읽기·쓰기, .claude 설정 수정, 병합·push.

# 7. 커밋
브랜치 `worktree-cowork-to-room-k3`(기준 22d44cf). 코드 커밋 693719b, 이 보고서는 그 뒤 커밋에 들어 있다. Judge는 브랜치 머리 커밋을 판정한다.
