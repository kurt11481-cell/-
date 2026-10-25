# Judge 지시문: kiwoom-block 변경 검토 (읽기 전용, 파일 수정 금지)

대상: 이 워크트리(kiwoom-block)의 변경(기준 7f98f28)과 Builder 보고서 docs/claude/kiwoom-block-builder-report.md.
지시문: E:\사업\##금동한\코덱스저장소\docs\claude\kiwoom-block-builder-prompt.md. 사장 승인: 사장실 스레드 직접 입력 "보강안 4개 진행"(2026-10-25 10:44:51Z).
키움 도구·CLI 실행, 비밀 읽기, 파일 수정은 하지 않는다. 훅·테스트는 합성 입력으로만 돌린다(테스트 실행은 허용).

검토 항목 (각각 PASS/FAIL + 근거 file:line)
1. 변경 파일이 지시문 "허용 파일"뿐인지(git status). `.claude/settings.json`·CLAUDE.md·tools/** 무변경.
2. docs/claude/kiwoom-block-settings-proposed.json vs 현재 .claude/settings.json: 기존 deny·ask 삭제·순서변경·약화 0, 추가는 deny 최대 5줄과 hooks 절뿐. JSON 유효. 허용(allow)·권한 확대 0.
3. kiwoomcli 영향 확인: 저장소 루틴이 셸에서 kiwoomcli를 직접 부르는지 직접 grep. 부르는데 deny 두 줄이 남아 있으면 FAIL.
4. 훅(.claude/hooks/kiwoom_order_block.py): 거절 표지 7종이 모두 있는지, fail closed(깨진 입력·필드 없음), 거절만 더하고 통과 조건을 넓히지 않는지, 우회 분기·환경변수 0, 파일 쓰기 도구는 검사 안 함. 거짓 음성 직접 시도(합성 입력): `KiwoomCLI.exe`, `overseas  orders`(공백 2개), 따옴표·인용 속 `"ust20001"`, `--confirm=true`, 명령 앞뒤 줄바꿈, `confirm: true`, 도구 이름 대소문자. 막히지 않는 변형이 있으면 FAIL 또는 PASS_WITH_FIX(수정안).
5. 훅 거짓 양성이 일상 작업을 막는지: `git status`, `python -m unittest`, `--confirmed-via`, 문서 grep 등 대표 명령 10개가 통과하는지.
6. settings의 hooks 절 형식(matcher·command)이 Windows에서 동작하는 형태인지, 모르면 보고서가 "확인 필요"로 정직하게 적었는지. 훅이 원격 장치 도구에 실제 발동한다고 단정했다면 FAIL.
7. ④ 문서(kiwoom-overseas-order-guard-2026-10-25.md): 결론이 safety.py·argument_maps.py·CSV·server.py 271~272행 원문과 맞는지 직접 열어 대조. 패키지 파일 수정 0.
8. 테스트: 새 test 파일을 직접 실행해 통과, 단언 약화·skip 0, 기준선 대비 새 실패 0. CRLF(.json)·ASCII(.py) 유지.
9. 권한·한도 확대 표현 0, 키움 호출·비밀 접근 흔적 0.

결론: PASS / PASS_WITH_FIX(수정안 명시, 줄 번호 고정) / FAIL. 파일은 고치지 않는다.
끝에 한국어로 사장에게 결론 먼저 3줄 이내로 보고하고, 마지막 줄을 "VERDICT: <결론>" 형식으로 쓴다.
