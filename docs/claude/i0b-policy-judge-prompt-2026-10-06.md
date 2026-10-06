# I0-b (나) 정책만 SIMPLIFY — K3 Judge 지시문 (2026-10-06)

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(Builder 창과 분리, 파일 수정 금지) · 이유: K3 Independent Judge — 승인된 정책(`alert_policy.json`) 의미 변경과 shadow cohort 이관의 독립 검토

- 대상: worktree `E:\사업\##금동한\코덱스저장소\.claude\worktrees\i0b-policy`(브랜치 `worktree-i0b-policy`, 커밋 전 변경). 기준 HEAD `dfca99d`.
- Builder 보고: 그 worktree의 `docs/claude/i0b-policy-builder-report-2026-10-06.md`. 자기보고이므로 증거로 쓰지 말고 diff·코드·테스트로 확인한다.
- 근거 문서: `docs/claude/i0b-fill-confirmation-design-2026-10-06.md`(설계 §5·§7-2·§8·§11), `docs/claude/i0b-policy-builder-prompt-2026-10-06.md`.
- 사용자 결정(Cowork, 2026-10-06): 결정 1 "예", 결정 2 "(나) 정책만 지금 수정", 결정 3 "MVLL+SOXL, gap·halt 일시 중단 수용". Builder 세션에서 정책 편집 계획에 "승인".
- Cowork 사전 확인(판정 아님, 읽기 전용): 바뀐 파일 11개 + 새 파일 3개(autocrlf 기준 git status). 정책 말단 경로 삭제 59개가 모두 `holding_timing_rules.positions.MVLL|SOXL` 아래, 추가는 `holding_timing_rules.positions`(빈 객체) 1개, 값 변경 0, `deployment_gate`·`holding_risk_rules` 동일. 새 정책 + 원본 폴더 실제 상태(revision 19)로 무결성 오류 `[]`, 상태 바이트 불변. 원본 폴더 `shadow_progress.json`은 HEAD와 같고 카운터 0.

## 1. 사용자 조작 (Windows 터미널, 한 단계씩)

1. `cd "E:\사업\##금동한\코덱스저장소\.claude\worktrees\i0b-policy"`
2. `claude` → `/model` Opus, `/effort` xhigh
3. 권한 창: 읽기, git 읽기 명령(status/diff/log/show), 테스트 실행은 허용. 파일 수정·쓰기, 이관 스크립트 실행, `apply`, 키움 접속, `.env`·토큰 읽기, 커밋·푸시는 거부.
4. 아래 2절 상자를 붙여 넣는다. 끝나면 Judge의 최종 보고(판정 + 발견 목록)를 그대로 Cowork에 붙여 넣는다.

## 2. 붙여넣기용 지시문

```text
역할: i0b-policy 독립 Judge (K3). 파일을 수정하지 않는다. 판정과 근거만 최종 메시지로 보고한다(한국어, 식별자는 영어, 70줄 이내).
금지: 파일 수정·생성(검증용 스크립트와 임시 사본은 작업 폴더 밖 scratch에서만), migrate_integrated_shadow_cohort.py 실행(쓰기), reconcile_broker_state.py apply·portfolio_review_journal.py apply 실행, 키움 접속·키움 도구, .env*·토큰·계좌번호 읽기·출력, 커밋·푸시. Builder 보고서는 자기보고이므로 증거가 아니다. 모든 결론은 diff·코드·테스트 재실행으로 확인한다.
참고: 저장소는 CRLF 파일이 많고 core.autocrlf=true다. 줄바꿈만의 차이는 변경으로 세지 않는다(git diff --ignore-cr-at-eol로도 확인).

먼저 읽기: 메인 폴더(E:\사업\##금동한\코덱스저장소)의 docs/claude/i0b-fill-confirmation-design-2026-10-06.md §0·§1-3·§1-7·§1-8·§5·§6·§7-2·§11, CLAUDE.md Hard safety·Change classes. 그다음 worktree의 Builder 보고서.

0. 범위
   - git status/diff로 변경이 정확히 이것뿐인지 확인한다. 수정 11: stock-strategy-system/alert_policy.json, workspace/state/integrated_shadow/shadow_progress.json, manage-us-stock-strategy/scripts/migrate_integrated_shadow_cohort.py, assets/locales/reconcile-broker-state-ko-KR.json, references/broker-snapshot-reconciliation.md, 테스트 6개(test_evaluate_timing_integration, test_portfolio_exposure, test_v2_5_leveraged_confirmation, test_v2_6_12_holding_valuation_shadow, test_v2_6_3_free_web_new_buy, test_v2_6_integration). 새 파일 3: workspace/state/integrated_shadow/cohorts/integrated-shadow-4f11526e20929f11/superseded_progress.json, tests/test_migrate_integrated_shadow_cohort.py, Builder 보고서. 그 밖의 변경이 있으면 FAIL 사유.
   - timing_engine.py·evaluate_alerts.py·kiwoom 관련 스크립트·assets/kiwoom-acceptance-pin-scope.json의 고정 27개·SKILL.md·assets/locales/ko-KR.json이 무변경인지 확인한다.

1. 정책 변경이 승인 범위뿐인가 (설계 Judge 1)
   - HEAD와 worktree의 alert_policy.json을 JSON으로 읽어 말단 키 경로를 비교한다. 바뀐 것이 holding_timing_rules.positions.MVLL·.SOXL 삭제뿐인지, 값 변경 0인지, 키 순서가 같은지.
   - 원문 diff에서 대상 블록 밖 바이트가 같은지(29줄 삭제, 1줄 추가). deployment_gate·holding_risk_rules·holding_timing_rules의 나머지 키(status, policy_version, formula_version, timing_feature_version, definitions, risk_overlay_rules, weakness_rearm, watch_confirmations)가 그대로인지.

2. 상태 쓰기·체결 기록·체결 추론이 없는가 (설계 Judge 2)
   - portfolio_state.json(worktree 사본)과 alert_runtime_state.json이 HEAD 시점 사본과 바이트 같은지. 새 코드·테스트에 confirmed_trades·confirmed_tranche_fills·timing_plan을 파일로 쓰는 곳이 없는지(T4의 메모리 사본 변경은 허용).

3. validator가 약해지지 않았는가 (설계 Judge 3) — 가장 중요
   - timing_engine.timing_anchor_errors, evaluate_alerts.leveraged_state_integrity_errors의 코드가 그대로인지.
   - 정책에서 positions가 비면 무엇이 검사에서 빠지는지 스스로 나열하고, 그것이 설계 §5 "잃는 것"과 사용자 결정 3(MVLL·SOXL anchor 검사, gap·halt watch-only, SOXL weakness_10ema, SOXL-R50 재무장 잠금)을 넘지 않는지 판단한다. 넘는 것이 있으면 FAIL 또는 사용자 결정 필요로 올린다.
   - 새 테스트 T1~T4를 직접 읽고, 각각이 주장하는 성질을 실제로 잡는지 판단한다. 특히 T2(positions가 비어도 holding_risk_rules 원가 한도·등록부 검사가 그대로 돈다)와 T4(timing_plan.policy_version 불일치는 여전히 F).
   - 수정된 기존 테스트 7곳(test_active_policy_generates_only_review_candidate, test_unreconciled_holding_change_fails_closed, test_v25_lv_07, test_inv_06 두 곳, test_int_12, test_first_stage_keeps_the_old_controls)이 단언을 지운 것이 아니라 새 승인 정책 기준으로 바꾼 것인지, 원가 한도 쪽 단언이 남아 있는지. RETIRED_TIMING_POSITIONS 상수가 HEAD 정책에서 지운 블록과 같은지.
   - 옛 정책(HEAD)으로 T1·T4가 통과하고 T2는 전제 줄에서만 실패한다는 Builder 주장을 scratch 사본으로 재현한다(선택, 시간이 되면).

4. 고정·배포 해시 (설계 Judge 4)
   - assets/kiwoom-acceptance-pin-scope.json의 required_implementation_paths 27개가 HEAD와 같은지(정규화 텍스트 기준). 이관 스크립트가 그 목록 밖인지.
   - deployment_gate의 required_source_* 6개가 현재 파일 정규화 해시와 일치하는지.

5. 실제 상태로 무결성 PASS (설계 Judge 5)
   - python -m unittest discover -s manage-us-stock-strategy/tests -p "test_evaluate_timing_integration.py" (14건 기대).
   - 메인 폴더의 실제 portfolio_state.json(revision 19)을 읽기만 해서, worktree 정책으로 leveraged_state_integrity_errors(state, policy, "2026-10-06") == [] 인지 확인한다(파일 쓰기 없이).

6. 소비처 영향 (설계 Judge 6)
   - build_holding_fact_pack._timing, portfolio_decision_dashboard 타이밍 투영, reconcile_broker_state.alert_engine_check가 빈 positions에서 예외 없이 설계 §5대로 동작하는지 코드로 확인한다.
   - test_portfolio_decision_dashboard의 실제 정책·실제 상태에 묶인 타이밍 테스트 묶음(Builder 보고 2-5의 3번)이 이번 변경으로 회귀를 숨기는지, 아니면 이미 r19로 실패 중이던 것을 그대로 둔 것인지 판단한다. 병합 차단 사유인지(차단/비차단) 명시한다.

7. cohort 이관 (설계 Judge 7)
   - 보관 파일의 prior_progress가 HEAD의 shadow_progress.json과 같고 카운터가 모두 0인지.
   - 새 shadow_progress.json의 바뀐 줄이 cohort_id·semantic_fingerprint·started_at뿐이고 CRLF 28줄인지. 저장 지문이 worktree에서 다시 계산한 지문과 같은지.
   - migrate 스크립트의 --reason 추가가 기본 동작을 바꾸지 않는지, enum 밖 값을 쓰기 전에 거부하는지, test_migrate_integrated_shadow_cohort 3건이 그것을 잡는지.
   - 보관 사유 HOLDING_BASELINE_SEMANTIC_CHANGE가 적절한지 판단한다. 이전 지문 차이에 5269cfd의 kiwoom-readonly-policy.json token_profile_alias 추가가 함께 들어 있다는 Builder 주장(2-5의 1번)을 확인하고, 사유 기록이 오해를 부르면 비차단 권고로 적는다.

8. 사용자 결정 기록 (설계 Judge 8)
   - 설계 문서 §8·§11에 결정 1~3과 gap·halt 일시 중단 수용이 기록돼 있는지. S7 2차 복구가 완료 기준으로 남아 있는지(설계 §4-C, §11).

9. 권한 (설계 Judge 9)
   - order_authority=false, quantity_authority=none, execution_quantity=null이 바뀐 파일 어디에서도 넓어지지 않았는지.

10. 문구(K0)
   - locale warning_TIMING_PLAN_TICKER_CHANGED의 "위" 방향이 render_proposal의 실제 출력 순서와 맞는지(reconcile_broker_state.py 177-187행 근처).
   - references 절차 4의 새 문장이 "원인을 모르면 적용하지 않는다"를 지키고, 나머지 절차(확인 코드, 재사용 금지, 예약 작업 금지)를 약화하지 않았는지. test_reconcile_broker_state가 통과하는지.

11. 대상 테스트 재실행
   - 설계 §7-2 목록 + test_portfolio_exposure + test_migrate_integrated_shadow_cohort를 모듈별로 돌려, Builder 보고 4-1 표와 같은지(새 실패 0) 확인한다. 환경 원인 실패(INTEGRITY_FAILURE, acceptance manifest 없음)는 HEAD 사본에서도 같은지로 구분한다.

최종 보고 형식:
- 판정: PASS / PASS_WITH_CONDITIONS / FAIL
- 항목 0~11 각각 한 줄(PASS/FAIL/비차단 권고 + 근거 파일:행 또는 명령)
- 병합 조건(있으면)과 병합 순서 의견(Builder 보고 6절 1번: 이 브랜치를 키움 재고정 9번 cohort 이관보다 먼저 병합)
- 비차단 권고 목록
```

## 3. 그다음 (Cowork)

1. Judge 보고를 받아 판정을 확인한다. FAIL이면 같은 Builder 창에서 최소 수정 지시문을 쓴다.
2. PASS면 사용자가 Builder 커밋·병합을 한다(명령은 그때 안내).
3. 병합 뒤 Cowork 확인: 원본 폴더 `alert_policy.json` 정규화 해시 `3F4E1BB5…`, 원시 해시 재측정, 실제 상태로 무결성 PASS, `shadow_progress.json` CRLF 28줄과 새 cohort `integrated-shadow-a0d3e69e9bc23a1b`.
4. 관제판: `r-i0b` 완료, 후속 K2(대시보드 타이밍 테스트 픽스처) 등록, 키움 재고정 9번 cohort 이관 순서 메모.
