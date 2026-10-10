---
id: redesign-t1-judge2-prompt-2026-10-10
title: 재설계 T1 독립 Judge 2차 — 조건 C1~C6·후속 2건 확인 (r3)
date: 2026-10-10
first_judge: docs/claude/redesign-t1-judge-report-2026-10-10.md (PASS-WITH-CONDITIONS)
builder_r3: .claude/worktrees/auto-core-t1/docs/claude/redesign-t1-builder-r3-2026-10-10.md
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃) · 이유: 1차 Judge 조건의 독립 확인**

## Judge
```
너는 독립 Judge다(1차 Judge와 같은 규칙). 파일을 고치지 않는다. 유일하게 쓰는 파일은
docs/claude/redesign-t1-judge2-report-2026-10-10.md 하나(메인 체크아웃). 키움 조회·kiwoomcli·auto_core.py daily·
reconcile_broker_state.py auto/apply 실행 금지, 커밋·병합 금지. Builder 보고는 증거로 쓰지 않는다.

1. docs/claude/redesign-t1-judge-report-2026-10-10.md의 "조건" 절과 worktree의 r3 지시문을 읽는다.
2. git -C .claude/worktrees/auto-core-t1 diff 74ad71e 로 C1~C6·T1B-1·T1B-2가 실제로 들어갔는지 항목마다 PASS/FAIL + 근거(파일:줄).
   - C1 세 재확인 각각의 거부 테스트가 있고 통과하는가
   - C2 guard가 scripts·schemas·assets 추적 파일 전체를 보고 apply 읽기 전에 FAIL 하는가
   - C3 warnings[]가 result·LATEST·스키마에 있고 기록을 막지 않는가
   - C4 (a) 전날 PENDING 금액 설명, (b) 사유가 D0뿐이면 streak 유지, 기준 오래됨 안내 — 체결이 2~3거래일마다 있어도 streak가 3에
     닿을 수 있음을 테스트로 보이는가
   - C5 FAIL 날 streak 증가 없음 / C6 별칭 없음 → 수집 전 FAIL, -KiwoomProfile 필수
   - T1B-1 .claude/settings.json deny에 정확히 4줄이 추가되고 다른 줄·allow·ask가 그대로인가
   - T1B-2 기대 문구만 바뀌고 뜻(스냅샷 + 사용자 확인 또는 불변 조건 자동 경로, 체결은 브로커 기록)이 유지되는가
3. 1차 판정 J1~J13이 r3 뒤에도 유지되는가(회귀만 확인): 범위, compare 무쓰기, 주문 경로 0, 현금 정의, 사람 경로 불변.
4. 테스트: test_auto_core·바뀐 테스트 파일 직접 실행, 전체 스위트는 test-runner 서브에이전트로 → 실패 집합 = 기준선 29개 −
   test_agent_rules = 28개인지 직접 비교. 테스트 수 감소 0.
판정 보고(한국어, 짧게): 맨 위 한 줄 PASS | PASS-WITH-CONDITIONS | FAIL, 그다음 항목표, 남는 조건(있으면).
```
