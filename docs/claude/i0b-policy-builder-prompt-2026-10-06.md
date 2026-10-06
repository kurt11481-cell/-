# I0-b (나) 정책만 SIMPLIFY — K3 Builder 지시문 (2026-10-06)

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree (`claude --worktree i0b-policy`) · 이유: K3 — 승인된 정책(`alert_policy.json`)의 의미 변경과 shadow cohort 이관

- 근거: `docs/claude/i0b-fill-confirmation-design-2026-10-06.md`(설계). 사용자 결정 2026-10-06(Cowork):
  - 결정 1 "예": 체결 기록 경로를 만들지 않고 목표를 설계 §2대로 바꾼다.
  - 결정 2 "(나) 정책만 지금 수정".
  - 결정 3 "MVLL+SOXL", "gap·halt 일시 중단 수용".
- 기준 blob(HEAD 기준, `git rev-parse HEAD:<경로>`). 다르면 차이를 보고하고 멈춘다.
  - `stock-strategy-system/alert_policy.json` `b593448f7058e4d7c0a1a1f01293027fd06dcad2`
  - `manage-us-stock-strategy/assets/locales/reconcile-broker-state-ko-KR.json` `8bfe61dbca13d7d23ac43ebdcbda5d36929ac17e`
  - `manage-us-stock-strategy/references/broker-snapshot-reconciliation.md` `ddcd3da2d8c9fcf096eaafe9af191153037dad97`
  - `manage-us-stock-strategy/tests/test_evaluate_timing_integration.py` `26cf61717b4c13e29a3cb27334f894ec32685bc9`
  - `workspace/state/integrated_shadow/shadow_progress.json` `4d7d3d52457b136136169025501530be67a53890`
- 작성 시점 HEAD: `5269cfd`(사용자가 이 문서와 설계 문서를 커밋하면 HEAD는 그 다음 커밋이 된다).
- 상태: 작성 완료, Builder 미실행. Judge 지시문은 Builder 보고 뒤 Cowork가 쓴다.

## 1. 사용자 조작 (Windows 터미널, 한 단계씩)

1. `cd "E:\사업\##금동한\코덱스저장소"`
2. 문서 2개 커밋(worktree는 커밋된 HEAD에서 만들어진다):
   `git add docs/claude/i0b-fill-confirmation-design-2026-10-06.md docs/claude/i0b-policy-builder-prompt-2026-10-06.md`
   `git commit -m "docs: I0-b minimal design and policy-only builder prompt"`
3. `claude --worktree i0b-policy`
4. 세션 안에서 `/model` → Opus, `/effort` → xhigh
5. 붙여 넣기: `docs/claude/i0b-policy-builder-prompt-2026-10-06.md 2절 상자 안의 지시를 그대로 따르는 Builder로 일해라.`
6. 권한 창: 읽기, 대상 파일 수정, 테스트 실행, worktree 안의 이관 스크립트 실행은 허용. 키움 실제 접속, `apply` 실행, `.env`·토큰 읽기, 커밋·푸시는 거부.
7. Builder가 정책을 고치기 직전에 바꿀 키 경로를 보여 주고 승인을 물으면, 내용이 `holding_timing_rules.positions.MVLL`·`holding_timing_rules.positions.SOXL` 삭제뿐인지 보고 `승인`이라고 답한다.
8. 끝나면 보고 파일 경로를 Cowork에 알린다. Builder 창은 닫지 않는다(수정 때 다시 씀).

## 2. 붙여넣기용 지시문

```text
역할: i0b-policy Builder (K3). 사용자 결정 2026-10-06: 결정 1 "예", 결정 2 "(나) 정책만 지금 수정", 결정 3 "MVLL+SOXL, gap·halt 일시 중단 수용".
먼저 읽기: docs/claude/i0b-fill-confirmation-design-2026-10-06.md의 §0, §1-3, §1-7, §1-8, §5, §6, §7-2, §8, §11. CLAUDE.md의 Hard safety와 Change classes.
금지: portfolio_state.json·reconciliation_ledger.jsonl·backups/ 수정(worktree 사본 포함), reconcile_broker_state.py apply·portfolio_review_journal.py apply 실행, 키움 접속·키움 도구, 주문 경로, 체결 기록 작성·체결 추론, 키움 acceptance 고정 27개(manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json) 수정, alert_policy.json의 deployment_gate·holding_risk_rules 수정, SKILL.md·assets/locales/ko-KR.json 수정, 스크립트 수정(아래 4번의 이관 스크립트 --reason 1건만 예외), 커밋·푸시, 줄바꿈 일괄 변환, .env*·토큰·계좌번호 읽기·출력.
없는 사실은 만들지 않는다(확인 필요). 보고는 한국어, 식별자는 영어.

0. 기준 확인
   - 지시문 머리의 blob 5개를 git rev-parse HEAD:<경로>로 확인한다. 다르면 보고하고 멈춘다.
   - worktree의 stock-strategy-system/portfolio_state.json(.worktreeinclude 사본)의 state_revision과 holdings를 기록한다(예상: 19, MVLL 278·NBIS 13·SOXL 75). 다르면 보고한다(멈추지는 않음).
   - 고정 27개 파일과 deployment_gate 대상 6개(timing_engine, evaluate_alerts, SKILL.md, builder, yfinance contract, output locale)의 정규화 해시를 기록한다(7번 대조용).

1. 사실 확인(읽기만)
   - holding_timing_rules.positions를 읽는 모든 코드에서 positions가 빈 객체 {}일 때의 동작을 확인한다. 최소: timing_engine.timing_anchor_errors·evaluate_holding_timing, evaluate_alerts.py 875행 근처 타이밍 반복, build_holding_fact_pack._timing, portfolio_decision_dashboard.py 357행 근처, shadow_acceptance 의미 지문, validate_mvll_volume_authority, validate_technical_snapshot, validate_research_packet. 빈 positions에서 예외·KeyError·"missing" 오류·fail-open이 생기는 곳이 있으면 멈추고 보고한다(결정 3의 전제가 깨짐).
   - 실제 정책 파일을 읽으면서 MVLL·SOXL 슬롯(tranche id, quantity 99/24, anchor 396/99)을 단언하는 테스트 목록.
   - 기준선: 설계 §7-2의 대상 테스트 모듈을 실행해 결과를 표로 남긴다. test_evaluate_timing_integration은 worktree 상태 사본이 r19라서 실패 5 + 오류 1이 예상된다(설계 §1-3). 다르면 보고한다.
   - workspace/state/integrated_shadow/shadow_progress.json의 카운터가 모두 0이고 목록이 모두 비었는지 확인한다. 하나라도 아니면 멈추고 보고한다.

2. 계획 보고와 승인
   - 바꿀 키 경로(holding_timing_rules.positions.MVLL, holding_timing_rules.positions.SOXL 삭제)와 "그 밖 바이트 불변"을 어떻게 지킬지 사용자에게 보여 준다.
   - 사용자가 이 세션에서 "승인"이라고 답한 뒤에만 3번으로 간다(CLAUDE.md: 승인된 정책 편집은 이 세션의 명시 승인 필요).

3. 정책 변경: stock-strategy-system/alert_policy.json
   - holding_timing_rules.positions의 MVLL·SOXL 두 항목만 지워 "positions": {}로 만든다.
   - JSON 전체를 다시 직렬화하지 않는다. 대상 블록만 잘라내고 그 밖의 키·값·순서·들여쓰기·줄바꿈(CRLF)은 그대로 둔다.
   - status, policy_version, formula_version, timing_feature_version, definitions, risk_overlay_rules, weakness_rearm, watch_confirmations 등 다른 키는 건드리지 않는다. policy_version을 그대로 두는 이유: 상태 timing_plan.policy_version과 달라지면 그 자체로 F다(timing_engine.py:39-41).
   - 변경 뒤: JSON 파싱 OK, 키 경로 diff가 위 2개뿐, 원시·정규화 sha256 전후, 줄 수와 CRLF 수를 보고한다.

4. shadow cohort 이관(K2)
   - migrate_integrated_shadow_cohort.py는 보관 사유를 GLOBAL_AUTHORITY_VOLUME_AND_DUAL_RUN_SEMANTICS_CHANGE로 고정해 쓴다(i4-r9-activation-report-2026-10-05.md §5-1). 선택 인자 --reason을 추가한다. 값은 schemas/superseded-shadow-cohort.schema.json의 enum 안에서만 받고, 기본값은 지금 값 그대로 둔다(기존 동작 불변). 테스트 3건: 기본값 유지, 지정값 기록, enum 밖 값 거부.
   - 1번의 카운터 0 확인 뒤 --reason HOLDING_BASELINE_SEMANTIC_CHANGE로 이관한다. 이 값이 이번 변경(타이밍 슬롯을 정책에서 뺌)에 맞지 않는다고 판단되면 이관 전에 멈추고 이유를 보고한다. 새 enum 값은 추가하지 않는다.
   - 이관 뒤 shadow_progress.json이 CRLF 28줄 그대로인지, 바뀐 줄이 cohort_id·semantic_fingerprint·started_at뿐인지, 새 보관 파일이 스키마 검증을 통과하는지 보고한다.

5. K0 문구
   - assets/locales/reconcile-broker-state-ko-KR.json의 warning_TIMING_PLAN_TICKER_CHANGED 값만 "주의: timing_plan 종목의 수량이 바뀝니다. 아래 '적용 후 알림 엔진 검사' 결과를 확인하세요."로 바꾼다. 다른 메시지는 그대로.
   - references/broker-snapshot-reconciliation.md 절차 4의 "(the alert engine may stop with STATE_MISMATCH until fills are confirmed through I0-b) or hold (do I0-b first)" 부분만 최소 수정한다. 내용: 타이밍 슬롯은 정책에서 빠졌으므로 anchor 오류는 나오지 않아야 한다. 적용 후 검사가 실패하면 적용 전에 사용자에게 알리고, 원인을 모르면 적용하지 않는다. 나머지 절차는 그대로.
   - 두 파일이 고정 27개·deployment_gate·설치 스킬 해시에 묶여 있지 않은지 먼저 확인한다. 묶여 있으면 그 파일은 고치지 않고 보고한다.

6. 테스트
   - 갱신: 실제 정책을 읽는 테스트의 MVLL·SOXL 슬롯 단언을 "타이밍 positions 없음" 동작 단언으로 바꾼다. test_evaluate_timing_integration.test_active_policy_generates_only_review_candidate는 MVLL-R25 후보 대신 "타이밍 후보 없음, 상태 STATE_MISMATCH 아님"을 단언한다. 엔진의 슬롯 동작 자체는 test_timing_engine의 합성 정책 픽스처가 계속 덮는지 확인한다(덮지 않으면 보고).
   - 새 fail-closed 테스트(합성 정책 사본 사용, 설계 §7-2):
     T1 타이밍 positions에 남아 있는 종목은 anchor 불일치면 여전히 STATE_MISMATCH.
     T2 positions에서 빠진 종목도 holding_risk_rules 검사는 그대로 돈다: NBIS 10% 경계 사례가 D, 등록부 밖 보유 종목은 STATE_MISMATCH.
     T3 변경 후 실제 정책 + worktree 상태 사본 → leveraged_state_integrity_errors == [], 실행 전후 상태 파일 바이트 동일.
     T4 상태 timing_plan.policy_version 불일치는 여전히 F.
   - 대상 모듈(설계 §7-2): test_evaluate_timing_integration, test_timing_engine, test_v2_5_leveraged_confirmation, test_v2_6_integration, test_v2_6_shadow_acceptance, test_build_holding_fact_pack, test_reconcile_broker_state, test_kiwoom_broker_shadow, test_portfolio_decision_dashboard, test_mvll_volume_authority, test_v2_6_12_holding_valuation_shadow, test_v2_6_3_free_web_new_buy, test_v2_6_7_session_aware_kiwoom_priority, test_state_write_boundary(고정 27개 중 하나라 고치지 않음, 이관 스크립트를 분석 경로 import 금지 목록에 둠), test_manual_portfolio_analysis(같은 목록), 이관 스크립트 테스트. 기준선 대비 새 실패 0.
   - 전체 스위트는 서브에이전트로 1회 돌리고 새 실패만 보고한다.
   - python manage-us-stock-strategy/scripts/validate_schema_contracts.py PASS.

7. 경계 확인(보고에 표로)
   - git diff --stat 파일 목록. 예상: alert_policy.json, shadow_progress.json, 새 보관 파일 1개, 이관 스크립트, 테스트들, locale 1개, reference 1개, 보고서.
   - 고정 27개 diff 0. deployment_gate 대상 6개 정규화 해시가 0번과 같음.
   - portfolio_state.json·원장·백업 diff 0(worktree 사본도 바이트 동일). holding_risk_rules 키 diff 0. 권한 3필드(order_authority=false, quantity_authority=none, execution_quantity=null) 불변.
   - 새 코드에서 confirmed_trades·confirmed_tranche_fills·timing_plan에 쓰는 곳 0(grep 결과 첨부).

8. 보고: docs/claude/i0b-policy-builder-report-2026-10-06.md
   - 기준, 사실 확인, 변경, 테스트 표(기준선 대비), 경계 표, 확인 필요, Judge가 볼 곳.
   - 커밋하지 않는다. 끝나면 마지막 줄에 "Builder 완료, worktree i0b-policy, 새 실패 수 N".

멈춤 조건: 0번 blob 불일치, 1번에서 빈 positions 예외·fail-open, cohort 카운터 0 아님, 고정 27개나 deployment_gate 대상 수정이 필요해짐, 상태 쓰기가 필요해짐, 원인 모를 새 실패.
```

## 3. 그다음 (Cowork)

1. Builder 보고를 읽고 Judge 지시문을 쓴다(설계 §7-2의 Judge 9항목).
2. 별도 Claude Code 세션에서 Judge(파일 수정 없음).
3. 사용자가 병합한다.
4. Cowork 병합 확인: 원본 폴더 `alert_policy.json` 원시·정규화 해시, 실제 상태(revision 19 이후)로 무결성 검사 PASS 재현, `shadow_progress.json` CRLF 28줄.
5. 관제판: `r-i0b` 완료 처리, `p-s7-p2` 완료 기준에 "MVLL·SOXL gap·halt watch-only 복구(예약 자동화 재개 전 필수)" 유지 확인.
