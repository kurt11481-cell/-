# Judge 지시문: kiwoom-block fix3 검토 (읽기 전용, 파일 수정 금지, 테스트 실행은 허용·필수)

대상: 워크트리 kiwoom-block-fix3의 변경(기준 c9c0877). 지시문 E:\사업\##금동한\코덱스저장소\docs\claude\kiwoom-block-fix3-prompt.md, 보고서 docs/claude/kiwoom-block-builder-report.md("fix3 반영" 절), docs/claude/kiwoom-block-fix3-report.md.
키움 도구·CLI 실행, 비밀 읽기, 파일 수정 금지. **테스트를 실제로 실행할 수 없으면 판정은 FAIL이 아니라 "확인 필요"로 적고 사장에게 알린다.**

S1. 변경이 허용 파일(test_dev_pipeline.py, test_kiwoom_order_block_hook.py, builder-report, fix3-report)뿐인지(git status). settings.json·훅·CLAUDE.md·tools/** 무변경.
S2. 직접 실행: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline*"`, `-p "test_kiwoom_order_block_hook.py"`, `-p "test_approval_human_check*"` 모두 새 실패 0(기대 126/23/28 안팎, 실제 수 기록). 이 워크트리의 .claude/settings.json은 병합 뒤 상태(deny 26줄)다.
S3. 단언 약화 0: 스크래치 사본에서 변이(deny 한 줄 삭제, 이상한 deny 한 줄 추가, hooks 키 삭제, ask 변경)를 넣으면 테스트가 실패하는지 직접 확인. 기준 7f98f28의 deny 23줄·ask 8줄 상수가 `git show 7f98f28:.claude/settings.json`과 같은지 대조.
S4. 보고서 정정(한계 추가, 28건 계산, 병합 뒤 확인, fix3 절, sha256 표)이 실제와 맞는지.
S5. 병합 전 상태(settings.json이 기준과 같을 때)에서도 두 테스트가 통과하도록 짜였는지 코드로 확인(실제로 settings를 바꾸지 말고 로직을 읽는다).

결론: PASS / PASS_WITH_FIX(수정안 줄 번호 고정) / FAIL. 파일은 고치지 않는다.
끝에 한국어로 사장에게 결론 먼저 3줄 이내로 보고하고, 마지막 줄을 "VERDICT: <결론>" 형식으로 쓴다. 답변에 S별 판정표를 포함한다.
