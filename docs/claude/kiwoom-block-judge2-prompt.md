# Judge 지시문: kiwoom-block fix1 재확인 (읽기 전용, 파일 수정 금지)

대상: 워크트리 kiwoom-block의 변경(기준 7f98f28). 지시문 E:\사업\##금동한\코덱스저장소\docs\claude\kiwoom-block-fix1-prompt.md, 보고서 docs/claude/kiwoom-block-builder-report.md("fix1 반영" 절).
이전 Judge 결과: PASS_WITH_FIX, 수정안 F1~F5(사장 직접 입력 12:04:09Z).
키움 도구·CLI 실행, 비밀 읽기, 파일 수정 금지. 훅·테스트는 합성 입력으로만 돌린다.

재확인 항목 (각각 PASS/FAIL + 근거 file:line)
R1. 변경이 F1~F5 범위뿐인지(허용 파일 밖 0, settings.json·CLAUDE.md·tools/** 무변경).
R2. 훅 diff가 거절만 더하는지(통과 조건 확대 0, 우회 분기 0), STRIP_CHARS 변경이 의도대로인지.
R3. 합성 입력으로 직접: `--con\firm`, `kiwoom\cli`, `--con$'f'irm`, Monitor 도구 입력(표지 있음/없음/명령 없음) 거절·통과. Windows 경로 일상 명령(5건 이상)과 평범한 명령(10건 이상) 통과. 이전에 쓴 judge_hook_probe.py를 써도 된다.
R4. 제안 settings: matcher만 바뀌었는지, 기존 deny/ask 삭제·약화 0, 허용 확대 0, JSON 유효, CRLF.
R5. 문서 정정(F5 전부)이 grep·원문 file:line과 맞는지(KIWOOM_MCP_ALLOW_ORDERS 미참조 확인을 직접 다시, server.py 36·207~217행), 못 막는 예 추가, sha256 표 갱신이 실제 값과 같은지.
R6. 새 테스트 파일과 test_dev_pipeline*·test_approval_human_check* 실행, 새 실패 0, 단언 약화·skip 0.

결론: PASS / PASS_WITH_FIX(수정안 줄 번호 고정) / FAIL. 파일은 고치지 않는다.
끝에 한국어로 사장에게 결론 먼저 3줄 이내로 보고하고, 마지막 줄을 "VERDICT: <결론>" 형식으로 쓴다.
그리고 Judge 보고서 전체를 사장이 저장소에 남길 수 있도록, 마지막 답변 안에 F별 판정을 표로 포함한다.
