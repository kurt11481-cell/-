---
id: devq-api-judge-prompt
title: "devq-api 독립 Judge (읽기 전용)"
date: 2026-11-25
class: "K3 수동 경로 Judge. Builder와 다른 세션, Read·Grep·Glob만(시험 실행이 필요하면 아래 줄만)"
source: "docs/claude/devq-api-builder-prompt.md, docs/claude/devq-api-proposal-2026-11-25.md 2판"
---

worktree의 diff(기준 커밋 대비)를 읽고 아래 항목마다 PASS/FAIL과 근거(파일:행)를 표로 쓴다. 마지막 줄은 `VERDICT: PASS` 또는 `VERDICT: FAIL — <최소 수정 목록>`.

1. diff가 허용 파일 8개뿐이다(dev-run.ps1, devpipe.py, sdk_agent.py, requirements-sdk.txt, tools/dev_pipeline/README.md, docs/claude/devq-api-route.json, test_dev_pipeline_api_route.py, docs/claude/devq-api-report.md). 기존 파일 줄바꿈이 원래대로다. dev-run.ps1이 ASCII다.
2. `devq-api-route.json`이 `judge_enabled: false`다. pick-route가 작업 트리가 아니라 `git show HEAD:`만 읽고, approved_ref·approved_kst 형식이 틀리면 api가 아니다.
3. api 조건 전부(켜짐·끄기 파일 없음·그달 닫힘 없음·SDK 있음·key-present yes·남은 금액 ≥ 3)가 코드에 있고, 하나라도 아니면 subscription이다. builder 역할은 늘 subscription. 상한 상수 60·최소 3·Judge 예산 8이 코드 상수다(docs 파일로 못 바꿈).
4. 장부 합산이 actual 우선·없으면 reserve이고, 장부를 못 읽으면 subscription(fail closed). max_budget_usd = min(8, 남은 금액).
5. 키: dev-run.ps1 자기 환경에서 세 이름을 지우고, 키는 sdk_agent를 띄우는 그 `$psi.EnvironmentVariables`에만 들어간다(`$env:`·`set` 문자열 없음). sdk_agent는 읽자마자 지우고 CLI env에는 `ANTHROPIC_API_KEY`만 준다. `test_env`가 세 이름을 뺀다. 키 값이 어떤 파일·로그·stdout에도 나가지 않는다(시험 단언 포함).
6. SDK 옵션이 지금 Judge 명령과 같다(opus·xhigh·Read/Grep/Glob·mcp__* 금지·strict MCP·project 설정·permission-prompts none·같은 claude.exe·턴 상수) + system_prompt preset claude_code. 다른 값이 있으면 보고 (d)에 이유가 있고 Judge 독립성을 약하게 하지 않는다.
7. `parse_judge_envelope`·`builder_envelope_summary`·Builder 명령·재시도 횟수·보호 경로·authority-paths.txt·dev-merge.ps1이 그대로다. sdk envelope이 기존 파서로 PASS/FAIL이 지금처럼 읽힌다(시험).
8. 넘기기: is_error·turns ≤ 1이면 구독으로 1번만, api envelope 보관, 인증·잔액·한도류면 그달 닫힘. turns ≥ 2 실패·예산 초과는 넘기지 않는다(이중 비용 없음).
9. 새 기록 파일이 `Save-Records`·`Test-Records` 대상을 깨지 않는다(run 폴더 안 새 파일이 기록 해시 대조를 STOP시키지 않음).
10. 주문·키움·정책·상태와 무관하고, 실제 API 호출·사용자 환경 변수 변경·설치·삭제가 없다. 보고서 (a)~(f)가 있고 수량·금액·키 값·표지가 없다.

시험을 직접 돌려야 확인되는 항목만, 이 줄들을 쓴다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline_api_route.py"` · `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_dev_pipeline.py"`. 파일을 고치지 않는다.
