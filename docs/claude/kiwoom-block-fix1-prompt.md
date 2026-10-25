---
id: kiwoom-block-fix1-prompt
title: "kiwoom-block fix1 — Judge PASS_WITH_FIX 수정안 F1~F5 반영 (Builder 지시문)"
date: 2026-10-25
class: "권한(K3) 후속 수정. 차단만 늘림. 수동 경로 Builder(Opus·high) → Judge 짧은 재확인(Opus·xhigh) → 병합은 사장 PowerShell 한 줄"
source: "Judge VERDICT: PASS_WITH_FIX, 사장이 스레드에 직접 붙인 수정안 F1~F5 (2026-10-25 12:04:09Z). 원지시문 docs/claude/kiwoom-block-builder-prompt.md, 원보고 docs/claude/kiwoom-block-builder-report.md"
authority: "order_authority=false · quantity_authority=none · 키움 호출 0건 · 허용 확대 0건"
---

# Builder: kiwoom-block fix1

작업 위치: 기존 워크트리 kiwoom-block(기준 7f98f28, 미커밋 상태 유지). 커밋·push·병합 금지, CRLF 유지, .py·.json ASCII. 원지시문의 "원칙"과 "허용 파일"을 그대로 따른다(키움 도구·CLI·비밀 접근 0, settings.json·CLAUDE.md·tools/** 수정 0, 설치된 키움 패키지 수정 0). 줄 번호는 Judge가 현재 파일 기준으로 적은 것이니 **먼저 해당 줄을 열어 일치를 확인**하고, 어긋나면 문구로 찾는다. 판단이 안 서면 BLOCKED.md(첫 줄 = 이유).

## F1 훅 — Monitor 도구를 셸 도구로 추가
`.claude/hooks/kiwoom_order_block.py` 29행: `SHELL_TOOLS = ("Bash", "PowerShell", "Monitor")`. 7행 docstring에도 Monitor를 추가한다. Monitor 호출에 명령 필드가 없으면(ws만 쓰는 호출) 기존 규칙대로 거절(fail closed)이며 의도된 동작이다.

## F2 훅 — 백슬래시와 bash 인용 우회 제거
같은 파일 34행 `STRIP_CHARS`: 지우는 글자에 **백슬래시**를 추가한다(기존 `"` `'` `^` 백틱 유지). 그리고 `$` 바로 뒤에 `"`/`'`가 오는 경우(bash `$'…'`)의 `$`도 지운다. 정규식 예: `re.compile(r"[\"'^\\`]|\$(?=[\"'])")` (정확한 이스케이프는 Python에서 직접 검증해 확정). 32~33행 주석에 "bash의 백틱, `$'…'`, 백슬래시 줄바꿈 이스케이프"를 추가한다. 목적: `--con\firm`, `kiwoom\cli`, `--con$'f'irm`이 걸리게 한다. **거절만 늘린다**(검사 문자열을 한 번 더 정리해 보는 것이며 통과 조건을 넓히지 않는다).
Windows 경로가 든 일상 명령(예: `python C:\Users\...\x.py`, `Get-ChildItem E:\사업\##금동한\코덱스저장소\docs\claude`)이 여전히 통과하는지 테스트로 확인한다.

## F3 제안 settings — matcher에 Monitor 추가
`docs/claude/kiwoom-block-settings-proposed.json` 46행 matcher를 다음으로 바꾼다:
`"^(Bash|PowerShell|Monitor|mcp__.*[Kk][Ii][Ww][Oo][Oo][Mm].*|mcp__.*(device_bash|start_process|interact_with_process))$"`
그 밖의 줄은 바이트까지 그대로. 불변식 테스트(기존 deny/ask 그대로 등)는 계속 통과해야 한다.

## F4 테스트 — test_kiwoom_order_block_hook.py
- 268행 근처 `targets`(matcher가 덮어야 하는 이름 목록)에 `"Monitor"` 추가.
- 120행 뒤 거짓 음성 변형 목록에 3개 추가: `--con\firm`, `kiwoom\cli`, `--con$'f'irm` (3 셸 도구 모두에서 거절).
- 135행 앞에 `test_monitor_command_is_checked` 추가: Monitor 도구 입력의 `command`에 표지가 있으면 2, 평범한 명령이면 0, 명령 필드 없으면 2.
- 단언 약화·skip 금지. 기존 22개(또는 현재 개수) + 새 케이스가 모두 통과해야 한다. `test_dev_pipeline*`·`test_approval_human_check*`는 새 실패 0을 다시 확인.

## F5 문서
- `docs/claude/kiwoom-overseas-order-guard-2026-10-25.md` 16행과 `docs/claude/kiwoom-block-builder-report.md` 129행: **`kiwoom_cli`와 런타임 패키지는 `KIWOOM_MCP_ALLOW_ORDERS`를 읽지 않는다**(grep 0건). 스위치 ①은 MCP 주문 도구만 막는다. CLI 경로를 막는 것은 deny `overseas orders` 2줄 + 훅 + 지침뿐이라고 고친다. (지금 문장은 위험을 실제보다 작게 보이게 한다.) grep은 읽기만으로 직접 다시 해서 근거 줄을 적는다.
- 보고서 129행 "못 막는 예"에 brace 확장 `--confi{rm,rm}`, 명령 치환 `$(…)`, 변수 `${x}`를 추가한다(원본·수정본 모두 못 막음).
- guard 문서 36행: 근거 줄 번호를 "36·207~217행"으로 고친다(READ_POLICIES는 36행, `kiwoom_query`는 207~217행; server.py 열어 직접 확인).
- 보고서 63행의 "확인 필요"(matcher의 괄호 안 교대 지원)는 "해소: JS 정규식이라 괄호 안 교대가 된다"로 고친다. 확인은 Judge 판단을 인용하되 근거 출처를 적는다.
- 보고서 "병합 뒤 확인"에 추가: Monitor 도구로 `echo ust20000`을 실행해 보는 무해 시험(거절되면 정상).
- 보고서 sha256 표(142~148행)를 새 값으로 갱신하고, 바뀐 파일 목록과 F1~F5 diff를 보고서에 붙인다. 보고서 끝에 "fix1 반영" 절을 추가한다(원래 결론은 지우지 않는다).

## 하지 않는 것
D1·D2 결정 변경(둘 다 현행 유지 = 기본값), 새 표지 추가, deny 변경, 허용 파일 밖 수정.

## Judge 재확인 항목 (참고)
R1 변경이 F1~F5 안뿐 · R2 훅이 거절만 더함(통과 확대 0) · R3 `--con\firm`·`kiwoom\cli`·`--con$'f'irm`·Monitor 거절, 일상 명령·Windows 경로 명령 통과 · R4 제안 settings 불변식 · R5 문서 정정이 grep 근거와 맞음 · R6 테스트 전부 통과.
