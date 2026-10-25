---
id: kiwoom-block-fix3-prompt
title: "kiwoom-block fix3 — 병합 뒤 깨지는 테스트 3건 고치기 + 보고서 정정 (Builder 지시문)"
date: 2026-10-25
class: "권한(K3) 후속. 테스트와 문서만 고친다(훅·settings·deny 변경 0). Builder(Opus·high) → Judge(Opus·xhigh, 테스트 실행 필수) → 병합은 사장 PowerShell 한 줄"
source: "병합 c9c0877 이후 Judge(2026-10-25 22:52 KST 붙임, 원문 workspace/outputs/manual-bj/kiwoom-block/judge-2.txt) F9~F11. 3차 Judge가 놓친 점: settings.json이 바뀐 뒤에는 기존 테스트 3건이 실패한다."
authority: "order_authority=false · quantity_authority=none · 키움 호출 0건 · 허용 확대 0건 · settings.json·훅·deny 변경 0건"
---

# Builder: kiwoom-block fix3

작업 위치: **새 워크트리** `claude --worktree kiwoom-block-fix3`(기준 = 현재 main c9c0877, 이미 kiwoom-block이 병합된 상태). 커밋·push·병합 금지(미커밋 유지), CRLF 유지, .py ASCII. 키움 도구·CLI·비밀 접근 0, `.claude/settings.json`·훅·CLAUDE.md·tools/**·키움 패키지 수정 0. 판단이 안 서면 BLOCKED.md(첫 줄 = 이유).

## 사실 (먼저 직접 확인)
병합 뒤 `.claude/settings.json`(deny 26줄)이 제안 파일과 바이트까지 같다. 그래서 다음이 실패한다. **먼저 테스트를 실제로 돌려 실패를 재현하고 이름을 보고서에 적는다**(`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline*"`, `-p "test_kiwoom_order_block_hook.py"`, `-p "test_approval_human_check*"`). 재현이 안 되면 BLOCKED.md.
1. `manage-us-stock-strategy/tests/test_dev_pipeline.py` 1496행 근처 `test_settings_json_p9`: deny 개수를 `len(OLD_DENY | P9_DENY)`(23)와 정확히 비교한다.
2. `manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py` 302~310행 근처: `cls.current`가 살아 있는 settings.json이라 병합 뒤 "추가된 deny"가 빈 목록이 되어 "3줄 이상" 단언이 실패.
3. 같은 파일 312~314행 근처: 새 키 집합이 비어 `{"hooks"}`와 달라 실패.

## F9 테스트 (병합 전·병합 뒤 두 상태 모두 통과해야 한다)
- **허용 파일에 `test_dev_pipeline.py`를 추가한다**(지시문 사장 승인 범위: 이 두 테스트 파일과 보고서만).
- test_dev_pipeline.py: `KIWOOM_BLOCK_DENY = {"mcp__*__kiwoom_order_preview", "Bash(*overseas orders*)", "PowerShell(*overseas orders*)"}`를 이름 붙여 둔다(현재 settings.json에서 값을 읽어 정확히 맞춘다). `test_settings_json_p9`의 개수 단언은 "추가된 deny는 정확히 그 3줄이거나 없음(병합 전 상태), 중복 없음"으로 바꾼다. 포함(`>=`) 단언은 `OLD_DENY | P9_DENY`를 그대로 유지한다. **단언 약화 금지**: deny가 줄어들거나 임의의 줄이 늘어나면 실패해야 한다.
- test_kiwoom_order_block_hook.py: `ProposedSettingsOnlyAdd`는 현재 settings.json 대신 **기준 7f98f28의 deny·ask·키 목록을 상수로** 두고(`git show 7f98f28:.claude/settings.json`으로 읽어서 옮긴다, 23줄·ask 8줄·키 effortLevel/permissions/worktree) 제안 파일을 그것과 비교한다. 그리고 "실제 `.claude/settings.json`은 기준과 같거나 제안 파일과 바이트까지 같다"를 별도 테스트로 단언한다.
- 위 변경 뒤 세 테스트 묶음이 전부 통과하고(훅 23·dev_pipeline 126·approval 28 기대, 실제 수를 적는다) 새 실패 0, skip 0.
- 변이 확인(스크래치 사본에서만): deny에서 한 줄 삭제 / 이상한 한 줄 추가 / hooks 키 삭제 시 테스트가 실패하는지 보고서에 적는다.

## F10·F11 문서 (docs/claude/kiwoom-block-builder-report.md)
- "한계"에 우회 예를 추가: 인용 부호를 `$'...'`·따옴표 여러 개로 쪼갠 변형 중 정리본으로도 못 잡는 계열(보고서 329행 재현 참고: 예 `--con""firm` 앞뒤에 다른 인용을 섞은 변형)과 bash brace 확장·`$(...)`·`${x}`. 코드 보강은 이번 범위 밖(NO_CHANGE).
- 366행 근처 "경계 3개 × 4 도구 = 28건"을 "8건(2×4) + 20건(5×4) = 28건"으로 고친다(숫자 직접 다시 센다).
- "병합 뒤 확인"에 메인에서 위 세 테스트 묶음을 돌려 기대값을 적는다.
- 끝에 "fix3 반영" 절(재현된 실패 이름, 바꾼 줄, 변이 확인 결과, 테스트 수치, 새 파일·바뀐 파일 sha256)을 추가한다. 원래 결론은 지우지 않는다.

## 허용 파일
manage-us-stock-strategy/tests/test_dev_pipeline.py · manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py · docs/claude/kiwoom-block-builder-report.md (모두 기존 파일 수정) · docs/claude/kiwoom-block-fix3-report.md (새, 짧은 요약). 이 밖은 건드리지 않는다.

## Judge 확인 항목 (참고, **실행 필수**)
S1 변경이 허용 파일뿐 · S2 세 테스트 묶음을 **직접 실행**해 통과(병합 뒤 상태 그대로) · S3 단언 약화 0, 변이(deny 삭제·임의 추가·hooks 삭제)가 실패로 잡힘 · S4 보고서 정정 · S5 settings·훅 무변경.
