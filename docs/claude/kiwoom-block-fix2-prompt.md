---
id: kiwoom-block-fix2-prompt
title: "kiwoom-block fix2 — 2차 Judge PASS_WITH_FIX 수정안 F6~F8 반영 (Builder 지시문)"
date: 2026-10-25
class: "권한(K3) 후속 수정. 차단만 늘림(fix1 전 대비 회귀 0이 목표). Builder(Opus·high) → Judge 짧은 재확인(Opus·xhigh) → 병합은 사장 PowerShell 한 줄"
source: "2차 Judge VERDICT: PASS_WITH_FIX, 사장이 스레드에 직접 붙인 수정안 F6~F8 (2026-10-25 13:07:28Z). 앞 지시문 docs/claude/kiwoom-block-fix1-prompt.md"
authority: "order_authority=false · quantity_authority=none · 키움 호출 0건 · 허용 확대 0건"
---

# Builder: kiwoom-block fix2

작업 위치: 기존 워크트리 kiwoom-block(기준 7f98f28, 미커밋 유지). 커밋·push·병합 금지, CRLF 유지, .py·.json ASCII. fix1 지시문의 "원칙·허용 파일·하지 않는 것"을 그대로 따른다(키움 도구·CLI·비밀 0, settings.json·CLAUDE.md·tools/**·키움 패키지 수정 0, D1·D2 현행 유지). 줄 번호는 Judge가 현재 파일 기준으로 적은 것이니 **먼저 열어 일치 확인**, 어긋나면 문구로 찾는다. 판단이 안 서면 BLOCKED.md(첫 줄 = 이유).

## 결함 (2차 Judge, R2 FAIL)
훅 `find_marker`(59행 근처)가 "(원문, 따옴표만 지운 정리본)"을 "(원문, 새 넓은 정리본)"으로 **바꿔 끼웠다.** 새 정리본은 백슬래시와 `$` 앞 따옴표까지 지워서 `--confirm` 뒤의 경계(`(?![A-Za-z0-9_-])`) 노릇을 하던 글자가 사라진다. 그 결과 fix1 전 훅이 막던 입력(예: bash에서 정확히 `--confirm`이 되는 `--con""firm$'\0'`, `--con''firm$'\x00'`)이 지금은 통과한다. "거절만 늘었다"는 fix1 보고 문장은 사실과 달랐다. 목표: **fix1 전 훅이 거절하던 것을 모두 거절 + fix1이 새로 잡던 것도 거절.**

## F6 훅 — .claude/hooks/kiwoom_order_block.py
1. 35행 주석을 두 줄로 바꾼다: 백슬래시+줄바꿈 변형(`--con\<newline>firm`)도 잡는다는 설명 뒤에 "The quote-only strip is checked as well, so a boundary that only the wider strip removes cannot hide a match: this can only add matches." 취지(영어, ASCII).
2. 36행 `STRIP_CHARS = …` 바로 앞에 한 줄 추가: `QUOTE_CHARS = re.compile(r"[\"'`^]")` (fix1 전의 정리 글자 집합과 같아야 한다. 이스케이프는 Python에서 직접 검증해 확정).
3. 59행 `find_marker`의 `for variant in (…)`을 **세 변형 모두 검사**하도록 고친다: (원문, `QUOTE_CHARS.sub("", text)`, `STRIP_CHARS.sub("", text)`). 하나라도 표지에 걸리면 거절. 통과 조건은 넓히지 않는다.

## F7 테스트 — manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py
- 거짓 음성 변형 목록(120행 뒤 근처, fix1에서 3+1개 추가한 곳)에 회귀 사례를 추가한다. 최소: `python -m kiwoom_cli domestic orders buy --con""firm$'\0'`, `python -m kiwoom_cli domestic orders buy --con''firm$'\x00'` (Python 문자열 이스케이프 주의; 셸에서 실제로 쓰이는 글자 그대로). Bash·PowerShell·Monitor·device_bash 모두 거절.
- 일반 회귀 방지 테스트 1개 추가: 입력 목록 전체(기존 거짓 음성 목록 + 위 2개 + `--con"firm\-x"`, `--con""firm\<newline>-x`, `python -c "f(a\con'firm'=True)"` 같은 경계 사례)에 대해 **fix1 전 방식(원문과 QUOTE_CHARS 정리본만 검사)이 거절하는 모든 입력을 현재 훅도 거절**하는지 확인한다(테스트 안에 fix1 전 방식을 참조 구현으로 작은 함수로 둔다; 훅 모듈의 표지 목록을 재사용하고 새 표지를 만들지 않는다).
- 단언 약화·skip 금지. 기존 22개 + 새 케이스 통과, `test_dev_pipeline*`(126)·`test_approval_human_check*`(28) 새 실패 0.

## F8 보고서 — docs/claude/kiwoom-block-builder-report.md
- 159행(결론 2)을 정정: "fix1 처음 판은 정리본을 바꿔 끼워, fix1 전에 걸리던 입력(`--con""firm$'\0'` 등, bash에서 `--confirm`이 됨)이 통과했다. fix2는 따옴표만 지운 정리본도 함께 검사해 fix1 전 거절을 모두 되살린다."
- 317행 R2 행: "fix1 처음 판은 아니오(judge2에서 회귀 확인), fix2 뒤 예"로 정정한다. 행 번호가 어긋나면 문구로 찾는다.
- 훅 35행의 옛 문구 "This can only add matches"가 fix2 후에도 사실인지 코드로 확인한다.
- 145·148행 sha256 표를 새 값으로 갱신하고 보고서 끝에 "fix2 반영" 절을 추가한다(바뀐 줄, 2차 Judge가 bash로 확인한 회귀 입력, 테스트 결과). 원래 결론과 fix1 절은 지우지 않는다.

## Judge 재확인 항목 (참고, 짧게)
R2 훅이 fix1 전 대비 회귀 0이고 fix1이 잡던 것도 잡음 · R3 이전 합성 입력(거절·통과) 결과 불변 · R6 테스트 전부 통과 · R1 변경이 F6~F8 범위뿐.
