---
id: recon-dayfill-k3-judge-prompt
title: "recon-dayfill-k3 Judge (읽기 전용)"
date: 2026-11-20
class: "K3 수동 경로 Judge — 파일을 고치지 않는다"
source: "docs/claude/recon-dayfill-k3-proposal-2026-11-20.md 7절"
---

Builder worktree의 diff와 docs/claude/recon-dayfill-k3-report.md를 읽고, 수정안 7절 J1~J7을 하나씩 판정한다. 각 항목에 근거(파일:행 또는 시험 출력)를 단다. 시험은 직접 다시 돌려 확인한다(`python -m pytest manage-us-stock-strategy/tests/test_auto_core_reconcile_dayfill.py manage-us-stock-strategy/tests/test_auto_core_reconcile_orddt.py -q` 및 전체). 하나라도 미달이면 FAIL.

추가로 본다: 창 계산에서 KST 후보 둘이 모두 들어오는 경우가 없는지(반열림 확인), DAY_SESSION 체결이 fills_after·fill_net·fill_sessions에서 정규 체결과 같은 길을 타는지, 정규·시간외 체결 dict가 바뀌지 않았는지.

금지: 파일 쓰기, 주문·키움 도구, apply, auto_core.py 실행, 비밀 읽기.

보고 마지막 비지 않은 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`.
