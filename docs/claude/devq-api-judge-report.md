---
id: devq-api-judge-report
title: "devq-api 독립 Judge 보고 (읽기 전용)"
date: 2026-11-25
judge: "회사PC 별도 세션(Opus 5.5 · xhigh), Builder와 다른 세션, 파일 수정 없음"
target: "worktree .claude/worktrees/magical-chatterjee-dc076d · 브랜치 worktree-devq-api · 기준 113727c5d66bb4d47c081d33e3a5af18121171ed · 커밋 없음"
prompt: "docs/claude/devq-api-judge-prompt.md"
---

이 파일은 Judge 세션의 답을 사장실 실행 스레드가 그대로 옮겨 적은 것이다(2026-11-25 KST).

| # | 판정 | 근거 |
|---|---|---|
| 1 허용 파일 8개·줄바꿈·ASCII | PASS | git status: 수정 3 + 새 파일 5. 기존 파일은 전부 CRLF(dev-run 658/658, README 104/104, devpipe 2565/2565줄). 새 파일은 LF. diff --stat과 --ignore-cr-at-eol 결과 같음. dev-run.ps1 비ASCII 0 |
| 2 꺼짐·HEAD만 읽음·형식 | PASS | devq-api-route.json:1 false. devpipe.py read_route_config(1433~)는 git show HEAD:만 읽고, 키가 정확히 3개가 아니거나 정규식에 안 맞으면 config_invalid |
| 3 api 조건·builder·상수 | PASS | pick_route 1502~: 켜짐→끄기 파일→그달 닫힘→키→SDK→남은 금액 기준. 하나라도 아니면 구독. 역할이 judge가 아니면 builder_stage1. 상수는 devpipe.py:120~122 |
| 4 장부·fail closed·예산 | PASS | month_spend 1484~: actual이 있으면 actual, 없으면 reserve. 장부를 못 읽으면 cap. 예산 = min(Judge 상한, 남은 금액)을 센트 아래 버림 |
| 5 키 | PASS | dev-run.ps1:28~30에서 키 이름 3개 삭제. 키는 Start-JudgeApi의 $keyEnv → Start-Captured:131~135 $psi.EnvironmentVariables에만 넣고, $env:·set 문자열 없음. sdk_agent.py:222(main 첫 줄)에서 7개 이름을 지우고 CLI에는 ANTHROPIC_API_KEY만 넘김(147행). test_env 612행. 키 미노출은 시험 단언으로 확인 |
| 6 SDK 옵션 = 지금 Judge | PASS | sdk_agent.py:134~149. opus·xhigh·Read/Grep/Glob·mcp__* 금지·strict·project·permission-prompts none·같은 exe·80턴, preset claude_code. 다른 값(max_budget, stream-json, env)은 보고 (d)에 이유 있음. 독립성이 약해지지 않음 |
| 7 바꾸지 않은 것·파서 | PASS | parse_judge_envelope(1356)·builder_envelope_summary(1404)·보호 경로·필수 플래그·Start-Builder·Invoke-Pipeline·재시도 모두 diff에 없음. authority-paths·dev-merge 변경 없음. SDK envelope이 기존 파서에서 PASS로 읽힘(시험) |
| 8 넘기기 | PASS | fallback_decision 1548~: is_error이고 턴 1 이하면 구독 1번. .api.json으로 보관. 401·403·429, 400+credit/limit이면 그달 닫음. 2턴 이상 실패·max_budget이면 넘기지 않음 |
| 9 기록 대조 | PASS | RECORD_ORDER(101행) 변경 없음. 새 파일은 기록 대상이 아님. 장부·표시 파일은 git이 무시하는 dev-runs 폴더 루트에 있음 |
| 10 무관·보고서 | PASS | 주문·키움·정책·상태 접점 없음. 보고서 (a)~(f) 있음. 금액·키 값·권한 표지 문자열 검색 0건 |

시험(지시문 두 줄, 바이트코드 쓰지 않음): test_dev_pipeline_api_route.py 47개 OK · test_dev_pipeline.py 162개 OK. 시험 뒤 worktree 상태 그대로.

참고(통과에 영향 없음): Judge·Builder 지시문은 worktree가 아니라 메인 체크아웃의 미추적 파일에서 읽음. 작업 전 실패로 envelope 비용이 비면 reserve가 그대로 남아 상한에 더 빨리 닿음(구독 쪽으로 돌아가는 보수적 방향).

보고서 docs/claude/devq-api-report.md sha256 = cae93b7cb3fd5d667f693b8d7f5a8a63b4f18cd1e991a545202b07c09cac04d4 (Builder 값과 일치)

VERDICT: PASS
