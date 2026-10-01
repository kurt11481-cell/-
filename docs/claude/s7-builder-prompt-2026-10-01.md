# S7 Builder 지시문 — S5 확정안 r2 정책 적용 (2026-10-01, K3)

- 목적: S7 사용자 승인(항목 1~7)을 받은 S5 확정안 r2를 정책·권한 원본·평가 코드에 반영한다. 출력은 목표 비중 표시뿐이다.
- 근거: `loss-limit-review-s5-policy-proposal-2026-10-01.md`의 "S5 확정안 r2"(R0~R9), "S6 Judge 판정"(재확인 2차 PASS), "S7 사용자 승인", 5절 diff r2, 9절(구현 범위·S6 요구 1~11·테스트 사례). 커밋 `88f6d4b`.
- 성격: K3(Production 의미·권한). approved policy(`alert_policy.json`)와 권한 원본(`workspace/policies/instrument_registry.json`) 변경, 고정 평가기 수정 가능성 포함. Builder → 별도 Judge(새 세션, 파일 수정 없음) → 사용자 커밋·병합.
- 권한: `order_authority=false`, `quantity_authority=none`, `execution_quantity=null` 유지. 이 작업으로 주문·수량 권한은 생기지 않는다.
- 기준값(10-01 Cowork 확인): `alert_policy.json` 원본 sha256 `184008bd…`, LF 정규화 `4a7c1492…`, blob `3d9df21a…`. `instrument_registry.json` 원본 `461c2887…`, LF `8d11aae8…`, blob `ade8807f…`. 정책의 `required_canonical_sha256`은 `750a0b4b…`(`validation_common.canonical_hash` 기준). 두 파일 모두 CRLF. 테스트 기준선(S4-3 Builder): 2058개 중 미통과 314(실패 22 + 오류 292).
- 상태: 작성 완료, Builder 미실행.

## 1. 사용자 조작 (Windows 터미널)

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree `s7-policy` · 이유: K3 정책·권한 원본·고정 평가기 변경, 교차 파일 설계**

1. 새 Windows 터미널에서 `cd "E:\사업\##금동한\코덱스저장소"`를 입력한다.
2. 이 지시문과 S5 제안서 진행 기록을 커밋한다(worktree는 커밋된 HEAD에서 만들어진다).
   `git add docs/claude/s7-builder-prompt-2026-10-01.md docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md`
   `git commit -m "docs: S7 builder prompt for S5 policy activation"`
3. `claude --worktree s7-policy`를 입력한다.
4. 세션 안에서 `/model`로 Opus, `/effort`로 xhigh를 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `docs/claude/s7-builder-prompt-2026-10-01.md 3절 상자 안의 지시를 그대로 따르는 S7 Builder로 일해라. 그 밖의 절은 참고만 한다.`
6. 권한 확인 창
   - 허용: 파일 읽기, `git status`/`log`/`diff`, python 테스트·해시 계산, worktree 안 파일 쓰기, sec.gov 접속, 키움 명세 문서 조회(`spec_search`·`spec_show`).
   - 거부: 키움 실행 도구(`kiwoom_query` 등 시세·계좌·주문), `.env` 읽기, worktree 밖 파일 쓰기(설치 스킬 `C:\Users\금동한\.codex\skills\` 포함), `reconcile_broker_state.py apply`, 커밋·push·merge.
7. Builder가 정지점에서 멈추면(1단계 조사, 2단계 계획) Cowork에 "S7 Builder 정지 N단계"만 보낸다. 내용은 worktree의 보고 파일(`docs/claude/s7-builder-report-2026-10-01.md`)에 있어 Cowork가 직접 읽는다.
8. 끝나면 "Builder 완료, worktree s7-policy, 새 실패 수 N"만 전한다. 커밋·병합은 별도 Judge 판정 뒤 Cowork 안내로 한다.

## 2. Cowork 사전 확인 (읽기 전용, Builder가 다시 확인한다)

| # | 확인 | 근거 |
|---|---|---|
| C1 | `deployment_gate` 고정 6개: `scripts/timing_engine.py`, `scripts/evaluate_alerts.py`, `SKILL.md`, `scripts/build_market_snapshot.py`, `references/yfinance-data.md`, `assets/locales/ko-KR.json`. 판정은 원본 = 설치 = required = observed(UTF-8 BOM 제거 + LF 정규화 해시) | `validate_skill_deployment.py` `ARTIFACTS`, `validate_deployment` |
| C2 | 키움 acceptance 고정 구현 파일 16개. `kiwoom_runtime_bridge.py`(키움 REST 유일 경로), `build_kiwoom_market_snapshot.py`, `session_aware_market_data.py`, `run_manual_portfolio_analysis.py`, `tests/test_manual_portfolio_analysis.py` 포함 | `kiwoom-acceptance-pin-diagnosis-2026-09-29.md` 2-1절 |
| C3 | 키움 일봉 종가는 시간외·야간 값이 섞인다. 그래서 R1·R4 종가는 16:00 표기 30분봉 종가다. repo의 키움 경로는 일봉(`usa06012`, `daily_chart`)만 읽는다 | `mvll-holding-card-2026-10-01.md` 정정 절, `kiwoom_runtime_bridge.py` `RUNTIME_APIS` |
| C4 | 분봉 API는 `usa06011`(미국주식 분 차트). 일봉과 같은 `/api/us/chart`, `tic_scope`(분 단위), `upd_stkpc_tp`(수정주가), `cont-yn`/`next-key` 연속조회. 응답에 정규장 구분 필드는 없고 `cntr_tm`(시각대 미기재)·`bus_dt`만 있다. 이력 깊이는 명세에 없다(확인 필요) | 키움 명세 `usa06011` |
| C5 | `portfolio_state.json`은 git 무시 대상이라 worktree에 없다. `timing_plan.positions`가 상태 안에 있고, `reconcile_broker_state.py`는 `timing_plan`을 쓰지 않는다(never_touched). 즉 timing_plan을 바꿀 승인된 쓰기 경로가 지금 없다 | `.gitignore`, `broker-snapshot-reconciliation.md` |
| C6 | `stock-strategy-system/decision_journal.json`은 아직 없다 | 파일 목록 |
| C7 | `alert_policy.json`을 참조하는 정책: `event_risk_policy.json`(`source_policy`), `mvll-volume-authority-policy.json`(`holding_timing_rules.definitions.pullback_reclaim_relative_volume_minimum`), `shadow_acceptance_policy.json`(`required_baseline_tickers` NBIS·MVLL·SOXL). 예약 런타임 worktree(`E:/사업/##금동한/runtime/stock-strategy-scheduled`)는 `main` 브랜치라 이번 병합만으로는 바뀌지 않는다(배포 절차 확인 필요) | grep, `git worktree list` |
| C8 | `decision_harness.approved_rule_registry`는 dict 7개(예: `soxl_max_loss_review` = status "approved", symbol, allowed_actions ["reduce","sell"], quantity_authority "none"). 실적 금지 구간은 종목 목록이 아니라 문장 규칙이다 | `alert_policy.json` |
| C9 | 상품 등록 선례: LMT production 반영(`production-policy.patch`, rollback handoff, 독립 Judge 패키지). 미추적 폴더라 worktree에 없고 원본 폴더 절대경로로 읽는다: `E:\사업\##금동한\코덱스저장소\workspace\outputs\lmt-instrument-registry-prod-act\` | 파일 목록 |
| C10 | 키움 30분봉 이력 길이(라이브): 미실시, 확인 필요. Cowork가 Builder 2단계 검토 전에 읽기 전용으로 확인해 전한다 | — |

## 3. 지시문

```text
역할: S7 Builder(K3). S7 사용자 승인을 받은 S5 확정안 r2를 정책·권한 원본·코드에 반영한다.
보고는 한국어, 식별자·명령·파일명은 영어. 자기 보고가 아니라 diff·해시·테스트 출력으로 보인다.

읽을 것(읽기만, 이 순서):
1. CLAUDE.md
2. docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md 중 "S5 확정안 r2", "S6 Judge 판정", "S7 사용자 승인", 5절, 9절.
   0~4·6절과 부록 B·C는 이력이다. 확정안 r2와 다르면 확정안 r2가 우선한다.
3. 이 파일 2절(Cowork 사전 확인). 직접 다시 확인한다.
4. docs/claude/kiwoom-acceptance-pin-diagnosis-2026-09-29.md 2-1절(고정 파일 16개)
5. manage-us-stock-strategy/references/broker-snapshot-reconciliation.md (R6 조사 때)
6. (있으면) graphify-out/GRAPH_REPORT.md는 위치 찾기에만 쓴다(증거 아님). git 무시 대상이라 worktree에는 없을 수 있다.

승인 범위(이 밖이 필요하면 멈추고 묻는다):
- S7 승인 1~7: 채우기 권고 = 미검증 사용자 위험 예산의 수익 추구 권고(표시 전용, 알림 B 이하, 수량 권한 없음) /
  R5 고점은 S7 적용일 이후 정규장 종가 최고치(전향) / 줄이기 순서 ① 종목 상한 초과(MVLL 포함) ② 카드 TRIM·EXIT ③ SOXL /
  위험 예산 1.55 유지 / 신규 매수 상품 승인 BE·MU·NBIS·DELL·AMD·SOXL·TQQQ·DRAM(MVLL·NBIL 미승인) /
  DRAM 종목 상한 0.4배 적용 / SOXL weakness_10ema 감시와 감소 뒤 EMA 재무장 규칙 은퇴.
- 5절 diff r2: 새 섹션 portfolio_exposure_policy·portfolio_review_lines, 기존 키 #1~#8·#12~#14.
- 9절: 계산·원장·가상 운용·표시, S6 요구 1~11, 테스트 사례.

절대 규칙:
- 주문·수량: 모든 새 규칙·출력에 order_authority=false, quantity_authority="none", execution_quantity=null을 유지한다.
  출력은 목표 비중만. 주문 수량·금액·주문 지시를 만들지 않는다.
  키움 실행 도구(시세·계좌·주문)는 쓰지 않는다. 명세 문서 조회(spec_search·spec_show)만 허용.
  .env*, 토큰, 계좌번호를 읽거나 출력하지 않는다.
- 값 고정: 1.55, 1.85, 1.25, 1.9, 0.4, 0.30, L1 0.90·L2 0.80·이후 0.10 간격, HWM 시작 28473.94(2026-09-30),
  V 창 252·최소 60, broker_snapshot_max_age_calendar_days 4, 연산자(≥, ≤, 반올림 전 비교)를 바꾸지 않는다.
- 고정 파일:
  · 키움 acceptance 고정 16개는 고치지 않는다(특히 run_manual_portfolio_analysis.py, tests/test_manual_portfolio_analysis.py,
    kiwoom_runtime_bridge.py). 필요해 보이면 멈추고 묻는다(별도 K3).
  · deployment_gate 고정 6개 중 scripts/build_market_snapshot.py, references/yfinance-data.md는 고치지 않는다.
    timing_engine.py, evaluate_alerts.py, SKILL.md, assets/locales/ko-KR.json은 승인된 계획에 있을 때만 고치고,
    고치면 deployment_gate 해시를 계획(P5)대로 처리한다(정규화: validate_skill_deployment.normalized_text_sha256).
- 상태·원장: portfolio_state.json, reconciliation_ledger.jsonl, backups/, 실제 decision_journal.json을 만들거나 쓰지 않는다.
  테스트는 픽스처와 임시 폴더만 쓴다. reconcile_broker_state.py apply를 실행하지 않는다.
- 정책 파일: workspace/policies/ 중 instrument_registry.json만 바꾼다. 다른 정책 파일(shadow_acceptance_policy.json,
  integrated_identity_session_activation.json 등)을 바꿔야 하면 멈추고 묻는다.
  alert_policy.json은 5절 r2 경로와 승인된 계획의 deployment_gate·policy_version만 바꾼다.
  다른 정책이 참조하는 키(예: holding_timing_rules.definitions)는 남긴다.
- worktree 밖에 쓰지 않는다(설치 스킬 C:\Users\금동한\.codex\skills\, 예약 런타임 E:\사업\##금동한\runtime\ 포함).
- 줄바꿈: 기존 파일의 줄바꿈·BOM·들여쓰기·키 순서를 유지한다. 일괄 변환 금지.
  JSON은 의도한 키 경로만 바뀌었는지 키 경로 diff로 보인다.
- 신원: MU·DELL·AMD·TQQQ 등록 값은 1차 출처로만 채운다(주식은 SEC EDGAR 10-K, TQQQ는 ProShares Trust의 SEC 제출
  투자설명서). 레버리지 배수도 공식 문서로 확인한다. 확인하지 못하면 그 상품에서 멈추고 보고한다(추정·Yahoo 금지).
- 결정론: 노출·선·권고 값은 결정론적 계산으로만 낸다. LLM 판단으로 값을 채우지 않는다. 계산 불가는 R0로 fail-closed.
- 결과를 보고 규칙·임계값을 바꾸지 않는다. 확정안 r2와 코드 현실이 충돌하면 멈추고 묻는다.
- 커밋은 별도 Judge 판정 뒤 내 승인이 있을 때 worktree 브랜치에만. push·merge·force 금지.

단계:
0. 기준선
   - git status, HEAD(88f6d4b 다음 문서 커밋 1개 예상), alert_policy.json·instrument_registry.json 원본·LF 해시(2절 기준값과 대조).
   - deployment_gate 6개와 acceptance 고정 16개의 정규화 해시를 기록한다(4단계에서 다시 대조).
   - 전체 테스트를 서브에이전트로 1회(실패만 보고, 실패 ID 목록은 파일로 저장):
     python -m unittest discover -s manage-us-stock-strategy/tests
   - 보고 파일 docs/claude/s7-builder-report-2026-10-01.md를 만들고 0절에 적는다.
1. 조사(읽기만) → 보고 파일 1절 → 멈춘다. 항목마다 file:line 근거, 모르면 "확인 필요".
   a. 바꿔야 할 파일 목록, 각 파일의 고정 여부(deployment_gate 6, acceptance 16)와 K 등급. 최소 파일 집합을 제안한다(요구 1).
   b. holding_risk_rules를 읽는 8개 스크립트에서 원가 한도를 판정에서 내리면 생기는 동작
      (보유 등록부 역할, freeze 키가 없을 때 기본값 true, hard-risk·D 등급 경로).
   c. timing_engine.py: 슬롯이 없으면 gap·halt 감시가 사라지는 지점, 상태의 timing_plan.positions(SOXL·MVLL)가 슬롯 은퇴 뒤
      어떻게 읽히는지, 상태 쓰기 없이(2절 C5) 처리할 수 있는지(요구 3).
   d. alert_policy.json·instrument_registry.json 변경이 닿는 곳: deployment_provenance.py·run_deployment_provenance.py,
      예약 경로 verify_current_provenance, shadow_acceptance.py 의미 해시와 required_baseline_tickers, 2절 C7의 참조 정책,
      integrated_identity_session_activation.json(요구 2).
   e. 상품 등록: registry 형식, canonical_hash 계산, required_canonical_sha256·캐시 동기화, new_buy_instrument_approved를 읽는
      스크립트(validate_research_packet.py, validate_decision_record.py, run_tactical_opportunity_radar.py,
      build_new_buy_strategy_draft.py), 승인 값 외 필드(DRAM candidate_status "reference_only" 등)가 게이트에 영향을 주는지(요구 10).
      바꿀지는 정하지 않고 2단계 결정 요청으로 올린다.
   f. approved_rule_registry 형식, validate_research_packet.py의 allowed_actions 어휘, 은퇴 표시 방법(요구 11).
   g. V 가격 이력(요구 9): 2절 C3·C4를 확인하고, 고정 파일(kiwoom_runtime_bridge.py)을 건드리지 않고
      usa06011 30분봉으로 252세션 정규장 종가 이력을 얻는 경로가 있는지. cntr_tm 시각대, 수정주가 처리, 조기 폐장일 봉을 적는다.
      라이브 조회는 하지 않는다(Cowork C10).
   h. reconcile_broker_state.py에서 R6 입출금 신고가 들어갈 자리(제안 해시·확인 코드·원장), 미결제 매도 대금 처리(요구 5).
   i. HWM·선 발동·멈춤·R5 고점의 저장 방법(요구 4). 두 안을 비교한다.
      (A) 저장 없이 재계산: 대조 원장(보유 이력) + 정규장 종가 이력 + 입출금 신고에서 매번 계산하고,
          사람 확인이 필요한 것(검토 완료·멈춤 해제)만 decision_journal.json에 남긴다.
      (B) 새 상태 파일 + 확인 코드 쓰기 경로.
      어느 쪽이든 쓰기는 Cowork 대화의 사용자 확인에만 묶고 예약 작업·Judge·Claude Code는 쓰지 않는다. git 무시 여부도 적는다.
   j. 표시 위치: render_holding_cards.py·validate_holding_card.py·portfolio_decision_dashboard.py·build_holding_fact_pack.py 중
      "E, 다음 선까지 거리, 멈춤 상태" 한 줄을 넣을 곳과 각 파일의 고정 여부.
   k. 영향 테스트(요구 8의 12개)와 원가 한도·슬롯·weakness_10ema·재무장을 단언하는 기존 테스트 목록.
   마지막 줄: "S7 Builder 정지 1단계".
2. 계획 → 보고 파일 2절 → 멈춘다. 내 승인 전에는 코드·정책을 고치지 않는다.
   - 파일별 변경 요약, K 등급, 고정 여부, 순서, 되돌리기 방법.
   - R0~R9 규칙 → 함수·파일 대응표. 새 계산은 순수 함수의 새 모듈을 우선한다(고정 파일 수정 최소화).
     검토 순서: NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD.
   - 결정 요청. 항목마다 선택지 2~3개 + 추천 1개와 이유. 한 항목씩 답할 수 있게 쓴다.
     P1 HWM·선·멈춤·R5 고점 저장 방법(1i)
     P2 알림 등급 매핑: L1, L2와 이후 선, E ≥ 1.85, E ≥ 1.9, R5, R0, 채우기(B 이하 고정)
     P3 30분봉 종가와 공식 종가 대조 허용 오차, 초과 시 처리
     P4 V 이력 출처(1g와 Cowork C10 결과에 따라). 키움으로 못 얻으면 무엇이 멈추는지 먼저 적는다.
     P5 deployment_gate 갱신 방법(required·observed·verified_at, 설치 스킬 동기화 전 상태와 그동안 막히는 것)
     P6 적용 순서: 정책 status·policy_version 값, "S7 적용일" 정의, 병합 뒤 Cowork·사용자 작업
        (HWM 재확인, 보유 종목 기준 카드, decision_journal 초기화, 설치 스킬 동기화, 예약 런타임 배포)
     P7 K132-G 보고 전용 원장을 이번에 할지, 별도 K2로 뺄지
     P8 1e에서 나온 등록부 필드 처리, 그 밖에 1단계에서 나온 미결정(없으면 "없음")
   - 마지막 줄: "S7 Builder 정지 2단계".
3. 구현(승인된 계획대로). 하위 단계마다 대상 테스트를 돌리고 보고 파일 3절에 결과를 적는다.
   3a 상품 등록(#12): 원본 수정 → required_canonical_sha256 → 캐시 동기화 → 확인
      python manage-us-stock-strategy/scripts/validate_registry_consistency.py --registry workspace/policies/instrument_registry.json --policy stock-strategy-system/alert_policy.json
   3b approved_rule_registry(#13): 7개 은퇴, S5 줄이기·채우기 규칙을 종목 단위로 등록(status "approved", quantity_authority "none").
   3c alert_policy.json 새 섹션 2개와 #1~#8·#14.
   3d 계산 모듈: N·V·E, R0, R2 대역·상한, 비중을 늘리는 권고(채우기·대역 안 신규 매수·교체 매수 쪽)의 예상 E ≤ 1.55와
      종목 상한, 줄이기 순서, R4 선, R5, R6 보류, 실적 금지 구간·실적일 미확인, MU 금지 구간 DRAM 대체 금지.
   3e 평가기·타이밍 엔진(계획에 있을 때): gap·halt 감시 유지, 은퇴 슬롯 무시, deployment_gate 처리.
   3f 대조 R6 신고(계획에 있을 때).
   3g 표시 한 줄.
   3h K132-G(P7에서 이번에 하기로 했을 때): 실제 계좌와 다른 파일, 실패해도 핵심 판단을 막지 않음, 정책 효과 없음.
4. 검증 → 보고 파일 4절
   - 대상 테스트 12개(요구 8) + 새 테스트. S6 필수 수정 5~11마다 fail-closed 테스트가 있어야 한다.
     python -m unittest discover -s manage-us-stock-strategy/tests -p "test_<name>.py"
   - 아래 "테스트 사례"를 테스트 이름과 하나씩 대응시킨 표.
   - python manage-us-stock-strategy/scripts/validate_schema_contracts.py
   - 3a의 validate_registry_consistency.py 명령
   - validate_skill_deployment.py: 원본 쪽 일치만 판정한다. 설치 쪽 불일치는 동기화 전 예상값으로 적는다(설치 폴더는 읽기만).
   - 0단계 해시와 대조: acceptance 고정 16개, build_market_snapshot.py, yfinance-data.md가 바뀌지 않았는지.
   - alert_policy.json·instrument_registry.json 키 경로 diff(바뀐 경로 전체)와 5절 r2 대응표. r2에 없는 경로가 있으면 이유.
   - 전체 테스트 서브에이전트 1회: 기준선 대비 새 실패 ID가 0개여야 한다.
5. 보고 → 보고 파일 5절: 바뀐 파일(K 등급), 키 경로 diff, 해시 전후, 테스트 결과, 확인 필요,
   병합 뒤 작업(P6 결정대로, Builder는 하지 않음), Judge가 볼 곳.
   마지막 줄: "Builder 완료, worktree s7-policy, 새 실패 수 N".
6. 커밋: 별도 Judge 판정 뒤 내 승인이 있을 때만, worktree 브랜치에만.

테스트 사례(9절 + R1·R2·R7에서 추가, 모두 필요):
- 선 경계: 정확히 닿음, 같은 하락 구간 1회, 새 HWM 재무장, 검토 "계속" 뒤 다음 선
- R0 트리거 7개 각각: 채우기·신규 매수 멈춤, 줄이기·경고는 "미확인" 표시로 계속
- V 이력 부족: 60 미만은 신규 편입 불가, 60~251은 가용 세션
- 0.4배 초과와 줄이기 순서, SOXL 없음 → "초과 미해소" 경고만(대체 없음)
- 비중을 늘리는 권고의 예상 E > 1.55 또는 종목 상한 초과 → 권고 생략(채우기·대역 안 신규 매수·교체 매수 쪽 각각)
- E ≥ 1.85 → 줄이기 + 신규 매수 멈춤, E ≥ 1.9 → 모든 신규 매수 차단 + 줄이기 "긴급"
- SOXL이 R5로 멈춤 → 채우기 생략(대체 없음)
- 실적 금지 구간, 실적일 미확인 = 금지 구간, MU 금지 구간에 DRAM 대체 금지
- 교체 두 단계: 매도 → 체결·주문 가능 현금 확인 → 매수(미체결 매도 대금은 현금 아님)
- R5 기준 고점 없음 → 그 종목 채우기 멈춤
- 입출금: 신고 한도 초과 거부, 미신고 → HWM·선 판정 보류 + 채우기·신규 매수 멈춤, 배당·수수료·세금은 입출금 아님
- (R1) 미등록 상품 보유 → E 계산 불가, 미등록 상품 신규 매수 권고 차단, MVLL·NBIL 신규 매수 불가
- (R2) 상품 승인 게이트가 열린 뒤에도 매수 제안은 watch_only·B 이하이고 후보를 만들지 않음(quantity_authority "none")
- (R7) 은퇴 규칙(원가 한도, SOXL·MVLL 축소 슬롯, weakness_10ema, 감소 뒤 재무장)이 알림을 내지 않고 gap·halt 감시는 남음
```

## 4. 진행 기록

- 2026-10-01 작성(Cowork). 근거: S5 제안서 "S7 사용자 승인" 절, 9절, 5절 diff r2. 2절 사전 확인은 읽기 전용(정책·상태 파일 무변경). 키움 명세 `usa06011`은 명세 문서 조회만 했다(라이브 호출 없음).
