---
id: kiwoom-block-hook-test-2026-10-26
type: record
status: current
as_of: 2026-10-26 09:12 KST
summary: "키움 주문 차단 보강 4건 마무리 기록 — 병합 두 번, 훅 발동 시험 결과, 아직 확인 필요한 것."
consumers: "사장 · 사장실 코디네이터 · 다음 권한 변경 작업"
authority: "order_authority=false · quantity_authority=none"
---

# 결론
키움 주문 차단 보강 4건이 끝났다. 병합 2번(main c9c0877, 5cf97e3), 훅은 이 PC의 새 Claude Code 세션에서 Bash와 Monitor 모두 `echo ust20000`을 막았다.

# 4건 처리
| 보강 | 결과 | 원문 |
|---|---|---|
| ① 앱 스위치 `KIWOOM_MCP_ALLOW_ORDERS` | 값 0 확인(사장 화면, 2026-10-26 07:53 KST). 이 스위치는 MCP 주문 도구만 막고 CLI는 막지 못한다 | docs/claude/kiwoom-overseas-order-guard-2026-10-25.md 결론 4 |
| ② deny 추가 | 3줄: `mcp__*__kiwoom_order_preview`, `Bash(*overseas orders*)`, `PowerShell(*overseas orders*)`. kiwoomcli 두 줄은 Cowork 루틴이 읽기 조회에 써서 제외 | .claude/settings.json, docs/claude/kiwoom-block-builder-report.md |
| ③ 주문 표지 훅 | .claude/hooks/kiwoom_order_block.py, fail closed. Bash·PowerShell·Monitor·kiwoom 이름 mcp 도구·장치 셸 도구 대상 | 같은 보고서 |
| ④ 주석·목록 불일치 | CSV(`guarded`)가 맞고 server.py 271~272행 주석이 틀림. 키움 CLI는 `--confirm`이 있으면 해외 주문을 실제로 보낸다. 패키지는 고치지 않음(제안 문구만) | kiwoom-overseas-order-guard 문서 |

# 발동 시험 (2026-10-26 09:08~09:12 KST, 이 PC 새 Claude Code 세션)
- Bash `echo ust20000`: 훅이 거절.
- Monitor `echo ust20000`: 훅이 거절(`PreToolUse:Monitor hook error ... order marker 'ust20000-ust20003'`). 처음 한 번은 세션이 스스로 실행을 거부해 판정이 나지 않았고, 사장 요청 시험임을 밝힌 두 번째 시도에서 확인.

# 아직 확인 필요
- 이 훅이 회사PC **원격 스레드**(mcp__remote-devices__* 도구)와 Cowork에서도 발동하는지. 위 시험은 PC의 대화형 Claude Code 세션이다.
- 훅이 못 막는 우회(PowerShell -EncodedCommand, 변수 이어 붙임, brace 확장, `$(...)`, `${x}`, 스크립트 파일 작성 뒤 실행): 마지막 선은 앱 스위치 0과 지침.
- 국내 주문 `kiwoom domestic orders ... --confirm`은 deny에 없고 훅 표지(`--confirm`, `kiwoomcli`)만 막는다.
- 사장 결정 D1(kiwoomcli 표지 유지), D2(--confirm 표지와 Cowork apply 겹침)는 기본값 유지. 막힘이 실제로 생기면 그때 다룬다.

# 교훈
settings.json을 바꾸는 병합은 병합 뒤 설정 기준으로 테스트를 병합 전에 돌려야 한다(1차 병합이 기존 테스트 3건을 깨서 fix3로 고침). 프로젝트 기억 premerge-tests-pin-settings.

# 관련 기록
Judge: kiwoom-block-judge-report.md, kiwoom-block-judge-post-merge.md, kiwoom-block-fix3-judge-report.md. 병합 스크립트: kiwoom-block-merge-2026-10-25.ps1, kiwoom-block-fix3-merge-2026-10-26.ps1.
