---
id: redesign-t1-builder-r3-2026-10-10
title: 재설계 T1 Builder 추가 지시 r3 — Judge 조건 C1~C6 + 후속 2건 (병합 전, 같은 worktree)
date: 2026-10-10
from: docs/claude/redesign-t1-judge-report-2026-10-10.md (메인 체크아웃, PASS-WITH-CONDITIONS) · 관제판 redesign-t1b
class: T1과 같음. 범위·금지는 docs/claude/redesign-t1-auto-core-builder-prompt-2026-10-10.md 3절 그대로, 단 아래 T1B-1의 .claude/settings.json deny 추가만 예외로 허용
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 기존 worktree `auto-core-t1` 이어서 · 이유: Judge 조건을 병합 전에 한 번에 반영(비교 기간을 최종 코드로 시작하기 위해)**

먼저 메인 체크아웃의 Judge 보고(E:\사업\##금동한\코덱스저장소\docs\claude\redesign-t1-judge-report-2026-10-10.md, "조건" 절)를 읽는다. 아래는 그 조건을 이 worktree에서 끝내는 지시다.

## 고칠 것
C1 apply_auto_core가 쓰기 직전에 다시 확인: ① workspace/policies/auto_core.json을 다시 읽어 mode=apply·kill_switch=false
   ② provenance를 다시 계산해 guarded dirty 경로 0 ③ 제안 cash_flow_declaration 존재 + status ∈ {NO_EXTERNAL_FLOW, DECLARED_IN_FULL}.
   셋 각각 어긋나면 쓰지 않음을 확인하는 테스트.
C2 apply 모드 guard = manage-us-stock-strategy/{scripts,schemas,assets}/ 아래 추적 파일에 미커밋 수정이 하나라도 있으면 읽기 전 FAIL
   (Judge가 제안한 가장 단순한 형태). 테스트.
C3 제안 warnings와 post_apply_checks.errors를 result.json·LATEST.json의 warnings[]에 싣는다(기록은 막지 않음). 스키마 갱신·테스트.
   (06:40 로더의 푸시는 배포 때 Cowork가 붙인다.)
C4 결제 당일(D0) HOLD가 streak를 끝없이 늦추지 않게: (a) 결제일이 오늘(KST)인 몫은 전날 실행의 reconcile.json I3.settlements에
   기록된 같은 결제일 PENDING 금액으로 설명한다. 전날 기록이 없으면 (b) 사유가 "D0 결제 미표시"뿐인 날은 streak를 유지(+1 없음,
   reset 없음)하고 사유를 남긴다. 둘 다 테스트. 추가로 compare 모드에서 기록 기준이 FILL_WINDOW 한도의 80%를 넘으면 FAIL 대신
   LATEST.next_action_for_user에 "기록 모드 켜기 필요(기준 오래됨)" 한 줄만 남긴다(한도 초과 자체는 지금처럼 쓰지 않음).
C5 30분봉·노출 등 어느 단계든 그날 status가 FAIL이면 streak를 올리지 않는다. 테스트.
C6 정책 token_profile_alias가 비었거나 없으면 auto_core가 수집 전에 FAIL. collect_30m.ps1의 -KiwoomProfile을 필수 인자로. 테스트.
T1B-1 .claude/settings.json permissions.deny에 4줄 추가(다른 줄은 건드리지 않음):
   "Bash(*auto_core.py*)", "PowerShell(*auto_core.py*)", "Bash(*reconcile_broker_state.py auto*)", "PowerShell(*reconcile_broker_state.py auto*)".
   Windows 작업(run_auto_core.ps1)은 Claude Code가 아니라 영향 없음. 이 파일은 줄바꿈·들여쓰기 원래대로.
T1B-2 tests/test_reconcile_broker_state.py test_agent_rules_require_snapshot_and_user_confirmation 기대 문구를 2026-10-10 CLAUDE.md·
   AGENTS.md 문구에 맞춘다. 뜻은 유지: "verified read-only broker snapshot" + (사용자 확인 경로 "reconcile_broker_state.py apply"
   또는 불변 조건 자동 경로 "auto-core … invariant"), 체결은 브로커 기록으로만. 기준선 실패 29 → 28이 되는 것이 정상.

## 완료 기준
- 대상 테스트 통과, 전체 스위트 실패 집합 = 기준선 29개에서 test_agent_rules 1개가 빠진 28개(새 실패 0), 테스트 수 감소 0,
  허용 경로(+ .claude/settings.json deny 4줄) 밖 변경 0, 스키마 감사 PASS. 키움 실제 호출 금지.
- Builder 보고에 "r3" 절(C1~C6·T1B-1·T1B-2 각각 바꾼 곳·테스트 이름)을 덧붙인다.
