# Judge 지시문: kiwoom-block fix2 짧은 재확인 (읽기 전용, 파일 수정 금지)

대상: 워크트리 kiwoom-block의 변경(기준 7f98f28). 지시문 E:\사업\##금동한\코덱스저장소\docs\claude\kiwoom-block-fix2-prompt.md, 보고서 docs/claude/kiwoom-block-builder-report.md("fix2 반영" 절).
이전 Judge 결과: 2차 PASS_WITH_FIX, R2 FAIL, 수정안 F6~F8(사장 직접 입력 13:07:28Z). 이전 Judge가 쓴 스크래치 도구(judge2_probe.py 등)가 이 PC의 임시 폴더에 있으면 써도 된다.
키움 도구·CLI 실행, 비밀 읽기, 파일 수정 금지. 훅·테스트는 합성 입력으로만 돌린다.

재확인 항목 (각각 PASS/FAIL + 근거 file:line)
R1. 변경이 F6~F8 범위뿐(훅·테스트·보고서). settings.json·CLAUDE.md·tools/**·키움 패키지 무변경, fix1 이후 제안 settings(46행 matcher)·guard 문서가 의도 없이 바뀌지 않았는지(sha256 대조).
R2. 훅: 세 변형(원문, 따옴표만 지운 정리본, 넓은 정리본)을 모두 검사하는지. fix1 전 훅(원문+따옴표 정리본만 검사)이 거절하던 입력을 현재 훅이 하나도 놓치지 않는지 합성 입력으로 직접 확인(회귀 0): `--con""firm$'\0'`, `--con''firm$'\x00'`, `--con"firm\-x"`, `--con""firm\<newline>-x`, `python -c "f(a\con'firm'=True)"`와 직접 만든 변형 10개 이상. 통과 조건이 넓어진 곳 0.
R3. 이전에 통과해야 했던 입력(Windows 경로 일상 명령 10개, 평범한 명령 15개)과 거절해야 했던 입력(`--con\firm`, `kiwoom\cli`, `--con$'f'irm`, Monitor 표지 있음/명령 없음 등)의 결과가 그대로인지.
R6. 새 훅 테스트·test_dev_pipeline*·test_approval_human_check* 실행, 새 실패 0, 단언 약화·skip 0. 회귀 방지 테스트가 실제로 fix1 전 방식과 비교하는지.
R8. 보고서 정정(159·317행 해당 문장, 훅 35행 주석, "fix2 반영" 절, sha256 표)이 실제 값·코드와 맞는지.

결론: PASS / PASS_WITH_FIX(수정안 줄 번호 고정) / FAIL. 파일은 고치지 않는다.
끝에 한국어로 사장에게 결론 먼저 3줄 이내로 보고하고, 마지막 줄을 "VERDICT: <결론>" 형식으로 쓴다. 답변에 R별 판정표를 포함한다.
