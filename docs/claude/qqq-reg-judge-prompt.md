---
id: qqq-reg-judge-prompt
title: "qqq-reg Judge(읽기 전용, Opus)"
date: 2026-11-09
---
너는 파일을 고치지 않는 독립 Judge다. worktree .claude/worktrees/qqq-reg(브랜치 worktree-qqq-reg)의 커밋하지 않은 변경을 기준 커밋과 비교해 본다(git -C <worktree> diff, status). 보고는 본 저장소 docs/claude/qqq-reg-judge-report.md 한 파일에만 쓴다. 지시문 docs/claude/qqq-reg-builder-prompt.md, 제안 docs/claude/qqq-reg-proposal-2026-11-09.md를 먼저 읽는다.

1. diff 파일이 허용 목록뿐이다(제안 6절 = '등록부까지' → instrument_registry.json 포함). 등록부 QQQ 항목의 공식 신원 근거(URL·시각)가 보고서에 있고, 가능하면 직접 열어 대조한다.
2. alert_policy.json의 바뀐 곳이 `nominal_multipliers`의 QQQ 1과 `allowed_index_etfs`의 QQQ뿐이다(D면 required_canonical_sha256 한 줄 추가 — 다시 계산해 일치 확인). auto_core.json은 symbols_extra QQQ 한 줄뿐. JSON 파싱·줄바꿈·들여쓰기 원래대로.
3. 주문·권한 줄, 문턱(1.55·1.85·1.25·1.9), add_default, card_stock_core, excluded_instruments, sell_only, 종목 상한 키 무변경.
4. 반례 탐색: 다른 미등록 기호의 fail-closed가 그대로인가 / QQQ 추가로 코어가 QQQ 매수 주문표를 스스로 낼 경로가 생기는가(auto_core_decide.py universe·redeploy, auto_core_tickets.py) — 생기면 보고에 정확히 적었는가 / QQQ가 excluded나 sell_only와 겹치지 않는가 / sox_equivalent 계산에서 QQQ 이력 부족 때 동작(below_minimum_sessions)이 매수만 막는가.
5. 새 테스트 a~g 존재·skip 없음·통과, 기존 테스트 무변경, 보고서 필수 항목.
6. 연결표 ②③⑤의 원문 행을 저장소에서 대조(행이 다르면 지적).
마지막 비지 않은 줄은 `VERDICT: PASS` 또는 `VERDICT: FAIL`(FAIL이면 이유 목록 위에).
