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
- 2026-10-01 Builder 1단계 조사 완료(HEAD `08b43a5`, 코드·정책·상태 무변경, 새 파일은 보고·기준선 실패 목록 2개). Cowork 검토와 C10 키움 실측은 5절. 다음은 Builder 2단계(5절 지침 반영).
- 2026-10-01 Builder 2단계 계획 완료, 사용자 결정 P0·P1·P2·P4-1·P4-2·P6·P7·P8-6(6절). P3는 Cowork 실측 뒤.
- 2026-10-01 Cowork 실측 C11~C15(7절), P3 결정(15:30 봉 종가), 3단계 지침(8절). 다음은 Builder 3단계(1차 구현).
- 2026-10-01 Builder 1차 구현 완료(보고 3~5절, 새 테스트 140, 전체 2198개 중 새 미통과 0). Cowork 읽기 전용 확인: 정책 키 경로 더함 177·지움 0·바뀜 0, 등록부·고정 파일 무변경, 새 테스트 7개 파일 VM 통과(대조 테스트 1건은 VM git 경로 문제로 난 환경 실패), 픽스처에 실제 계좌 자료 없음. 다음은 S7-1 Judge(`s7-1-judge-prompt-2026-10-01.md`).
- 2026-10-02 S7-1 Judge PASS_WITH_FIXES(필수 수정 6 + Cowork 추가 1, 9절). 다음은 같은 Builder의 최소 수정 → 같은 Judge 재확인.
- 2026-10-02 Builder 필수 수정 a~g 반영(보고 3.7, 재현 테스트 29개 수정 전 20개 실패 → 전부 통과, 전체 2228개 중 새 미통과 0). Cowork 확인: 정책 키 경로 더함 177·지움 0·바뀜 0 유지, `.claude/settings.json` deny 3줄만 추가, 새 테스트 8개 파일 VM 통과. 다음은 같은 Judge 창 재확인.
- 2026-10-02 S7-1 재확인 **PASS**(필수 수정 a~g 해소, 해석 5개 수용 — f는 U3에서 적요에 이름·자유 문구가 보이면 정확 일치로 좁히는 조건부, 전체 2228개 중 새 미통과 0, 고정 22개·정책·등록부 해시 그대로). Judge 참고: worktree는 CRLF라 달력이 ACTIVE로 안 잡힘(원본 폴더는 LF라 정상). 사용자 U12 승인: SOXX 30분봉 표본 픽스처 2개 커밋(원문 "커밋 승인 (추천)"). 다음은 Builder 커밋 → 사용자 병합.

## 5. Cowork 1단계 검토 (2026-10-01, 읽기 전용)

- 판정: 1단계 보고를 받아들인다. 핵심 주장 X1(슬롯 은퇴 시 `STATE_MISMATCH`), X2(정책 보유 종목 ⊆ 실제 보유 검사), X3(tactical universe 미포함·승인 불일치), X6(`kiwoom-readonly-policy.json` 허용 목록에 `usa06011` 없음), X8(현황판 위험 한도표 v0.2: 현금 하한 10%, 3배 ETF 상한 10%, 전체 조정 노출 상한 125%), X14(신원 범위에 MU·DELL·AMD·TQQQ 없음)를 Cowork가 원문 줄로 다시 확인했다. worktree 변경은 보고 파일 2개뿐이다.
- 지시문 2절 정정: 두 정책 파일 원본은 CRLF·LF 혼합이다(Builder 0.2가 맞다). C5의 `portfolio_state.json`은 worktree에 복사돼 있다. 읽기만 하고 쓰지 않는 규칙은 그대로다.

### 5.1 C10 키움 30분봉 실측 (Cowork, `kiwoomcli overseas candles stock-minute` = `usa06011`, 조회 전용, SOXX)

| # | 관찰 | 근거(요청) |
|---|---|---|
| K1 | 이력은 **2026-04-01부터**다. `--from 20260331`·`20251001`은 빈 결과, `20260401`은 그날 04:00 봉부터 나온다. 10-01 기준 약 125세션이라 **252세션 창은 채울 수 없다.** 6개월 이동 보관인지 고정 시작일인지는 확인 필요 | from 20251001·20260331·20260401·20260701·20260930 |
| K2 | 한 쪽(page)은 최대 100봉, 최신 → 과거 순서. 하루 봉은 04:00~27:30(야간 20:00~27:30도 같은 `bus_dt`), 약 48봉. 125세션 채우기는 종목당 약 60쪽, 이후 매일 1쪽 | 같음 |
| K3 | 봉 표기는 **시작 시각**이다(09:30 봉에 개장 거래량). 시각대는 ET로 보이나 서머타임 처리 확인 필요 | 9/29·9/30 봉 |
| K4 | **16:00 봉 종가에는 16:00~16:30 시간외 체결이 들어간다.** SOXX 9/30: 15:30 봉 종가 568.20, 16:00 봉 시가 568.64(마감 동시호가 체결로 추정)·종가 570.80(시가 대비 +0.38%). 공식 종가는 "16:00 봉 시가"에 더 가까울 수 있다(가설, 공식 종가와 대조 필요). r2·MVLL 카드의 "16:00 표기 30분봉 종가" 정의를 P3에서 다시 본다 | 9/30 15:30·16:00 봉 |
| K5 | 이상치가 있다: SOXX 6/30 16:00 봉 저가 482.15(앞뒤 봉 약 640). 시가·종가는 정상. 저가·고가를 쓰는 계산은 검증 필요 | 6/30 16:00 봉 |
| K6 | 쪽 마지막 행의 `upd_stkpc_tp`에 "1f"가 붙는다. 의미 확인 필요(수정주가 표시가 아닐 수 있음) | 각 쪽 끝 행 |

- r2 해석: R1의 "이력 252 미만이면 가용 세션(최소 60)"을 적용하면 V는 계산할 수 있다(약 125세션). 다만 이 문장은 상장 이력이 짧은 상품을 위한 것이었으므로, 데이터 보관 한계에도 적용할지는 사용자 결정이다(P4).

### 5.2 2단계 지침 (3절 2단계에 더한다)

1. 5.1을 P3·P4의 입력으로 쓴다. P4 선택지에는 적어도 (a) 고정 브리지·`kiwoom-readonly-policy.json` 확장(K3, acceptance 영향) (b) 고정 파일 밖 별도 수집기 + 가격 이력 증거 파일 (c) V·R4를 "미확인"으로 두고 R0로 멈춘 채 나머지만 적용을 넣고, 각각 무엇이 멈추는지 적는다.
2. 범위 밖 파일이 필요한 항목(X3 tactical universe, X6 키움 경로, X8 위험 한도표, X14 신원·시세 범위, X15 shadow cohort 상태)은 승인된 것으로 가정하지 않는다. 항목마다 "이번에 포함 / 별도 단계로 미룸 / 하지 않음" 선택지와 미뤘을 때 S7에서 빠지는 기능을 적는다.
3. 단계 나누기 안을 함께 낸다: (A) 한 번에 전체 (B) 나눠서 적용(예: 1차 = 승인 범위 안에서 지금 검증 가능한 것, 2차 = 범위 밖 의존). 어느 안이든 **옛 통제가 빠졌는데 새 통제가 판정하지 못하는 빈틈(fail-open)**이 생기면 그 구간과 영향을 표로 보인다. 추천 1개와 이유.
4. X1·X2·X7·X9·X12·X13·X16은 계획 본문에서 처리 방법을 제안한다(결정이 필요한 것만 P 항목으로).
5. X10: 설치 스킬 동기화 전까지 실패가 예상되는 테스트(`test_v2_6_integration`, `test_v2_4_automation` 등)는 ID와 이유를 미리 적어 "새 실패 0" 판정에서 따로 다룬다. Judge가 확인한다.
6. 결정 요청은 초보자가 한 항목씩 답할 수 있게 쓴다: 질문 한 줄, 선택지 2~3개(각 한 줄), 추천과 이유 한 줄. 사소한 것은 계획 기본값으로 묶고 목록만 보인다. 항목 수는 꼭 필요한 만큼.
7. 2단계도 코드·정책·상태를 고치지 않는다. 끝 줄 "S7 Builder 정지 2단계".

## 6. Builder 2단계 검토와 사용자 결정 (2026-10-01, Cowork 대화, 한 번에 하나씩)

- Cowork 검토: 2단계 보고(`s7-builder-report-2026-10-01.md` 2절)를 받아들인다. 1차는 고정 파일·범위 밖 파일 0개, 옛 통제 유지라 빈틈이 없다. 기본값 D1~D12는 따로 묻지 않고 적용한다. D1(줄이기·채우기 목표 = 예상 E 1.55)은 해석이 들어간 값이며 목표 1.55 결정과 같은 방향이다. `alert_policy.json`에는 스키마가 없어 새 최상위 섹션 추가로 검증이 깨지지 않는다(Cowork 확인).

| # | 질문 요지 | 사용자 답 |
|---|---|---|
| P0 | 적용 방식 | 나눠서 (추천): 1차 = 더하기만·옛 통제 유지, 2차 = 은퇴·#12·고정 파일 |
| P1 | HWM·선·멈춤·종목 고점 보관 | 매번 다시 계산 (추천). 사람 확인(적용 시작·검토 완료·멈춤 해제)만 `decision_journal.json`에 `확인 <코드>`로 기록 |
| P2 | 알림 등급 | D를 이어 씀 (추천): L1 = C, L2와 이후 선 = D, E ≥ 1.9 = D, E ≥ 1.85 = B, R5 = B, R0 = B("미확인"), 채우기 = B. `alert_grades.D` 문장 보강도 승인(2차 반영) |
| P3 | 정규장 종가 정의 | **15:30 봉 종가** (추천, 7.1 대조 뒤 결정): 시작 시각 표기 기준 정규장 마지막 30분봉(15:30~16:00)의 종가. 조기 폐장일은 폐장 직전 봉. "근사 종가"로 표시. 외부 공식 종가는 있으면 차이만 표시하고 자동 "미확인"은 하지 않는다. r2 JSON 값 `final_regular_session_30m_bar`와 같은 뜻이고, r2 R1 본문의 "16:00 표기 봉"은 이 결정으로 대체한다 |
| P4-1 | 30분봉 이력 출처 | 증거 파일로 수집 (추천): Cowork가 키움 공식 CLI(조회 전용)로 받은 쪽을 저장, repo 스크립트는 검증·정규화만 |
| P4-2 | 약 125세션으로 V 계산 | 예 (추천): 가용 세션(최소 60) 규칙을 보관 한계에도 적용, "짧은 이력" 표시, 계속 쌓아 252까지 |
| P5 | 고정 파일 해시 갱신 | 2차 지시문에서 묻는다 |
| P6 | S7 적용일 | 사용자 확인 기록 날짜 (추천). 1차 새 섹션 status `approved_display_only_old_controls_retained` |
| P7 | K132-G 원장 | 별도 K2로 뺌 (추천). 정책에는 설정만 |
| P8-1~5 | universe·위험 한도표·신원 범위·cohort·BE/DRAM 신원 | 2차 지시문에서 묻는다(Builder 추천: 2차/별도 작업/별도 K3/2차/별도 K3와 함께) |
| P8-6 | R6 입출금 신고 시점 | 계좌 실측 뒤 1차에 포함 (추천) |

- 다음: Cowork 실측(Builder 보고 2.9의 C11~C15) → 결과를 7절에 기록 → P3 질문 → Builder 3단계(구현) 지시.

## 7. Cowork 실측 C11~C15 (2026-10-01, 읽기 전용)

- 방법: 키움 `overseas candles stock-minute`(usa06011, 조회 전용)만 사용(서브에이전트 실행, 요약 수치는 Cowork가 CSV로 다시 계산해 일치 확인). 공식 종가 대조는 Yahoo 일봉 종가(참고용, Nasdaq.com 종가와 40/40 같음). 계좌·주문 명령 없음.
- 저장(커밋 안 함): `workspace/outputs/regular-session-closes/samples/` — `soxx_30m_20260930_p1.json`(100행), `soxx_30m_20260930_p2.json`(200행), `c12_close_comparison_20260917_20260930.csv`(40건), `README.md`. 거래소: SOXX·NBIS·MVLL = NASDAQ, SOXL = NYSE(키움 구분, 출처 `tests/fixtures/kiwoom/kiwoom-readonly-acceptance-20260813.sanitized.json`).

### 7.1 C12 종가 후보 대조 (SOXX·SOXL·NBIS·MVLL × 2026-09-17~09-30 10세션 = 40건, 허용 오차 max($0.05, 종가×0.1%))

| 후보 | 허용 오차 안 | 정확 일치(<$0.005) | 최대 |차이| | 평균 차이 |
|---|---|---|---|---|
| 15:30 봉 종가 | 33/40 | 2/40 | 0.268% | −0.012% |
| 16:00 봉 시가 | 34/40 | 16/40 | 1.226% | −0.019% |
| 16:00 봉 종가(r2 문자 그대로) | 13/40 | 1/40 | 1.042% | −0.118% |

- 16:00 봉 시가는 SOXX 7/10·NBIS 6/10 정확 일치지만 SOXL 1/10·MVLL 2/10이고, 거래가 적은 날은 크게 어긋난다(MVLL 9/18 −1.23%). 16:00 봉 첫 체결이 마감 동시호가가 아닐 수 있다.
- 공식 종가는 40/40 모두 16:00 봉의 저가~고가 안에 있었다.
- 키움 정규장 봉 거래량 합계는 통합 일 거래량의 38~70%다. 키움 분봉이 통합 체결이 아닐 수 있다(확인 필요).
- 기존 기록 영향: MVLL 카드의 자산 산식(SOXL 75×$149.40)은 16:00 봉 종가였고 9/30 공식 종가는 $147.86이다. HWM 시작값 $28,473.94는 적용일 재확인 때 P3 정의로 다시 계산한다(Builder 계획과 같음).
- 기존 정책: `web_completed_close_evidence_policy.json`은 웹 종가를 Shadow 교차 확인으로만 허용하고 Yahoo 출처를 거부한다. Nasdaq.com 경로는 `SOURCE_ROUTE_PENDING_REVIEW`다. 외부 공식 종가를 주 출처로 쓰려면 별도 K3다.

### 7.2 C11·C13·C15

- C11 조기 폐장: 2026-04-01~09-30에는 없다(`workspace/calendar-authority/artifacts/2421eeb7…/us-equities-core-session-v2.calendar.json`, 11/27·12/24만 13:00). 정책상 ACTIVE 달력(`d6d1ecd…`)은 8/29까지라 9월분은 확인 필요. 조기 폐장 표본은 11/27 이후에 받는다.
- C11 기타: `from=D` 조회는 D일 23:30 봉까지 나온다. 19:00·19:30 봉은 없다. 금요일 `bus_dt`에 20:00~27:30 봉(일요일 밤 세션으로 추정, 확인 필요).
- C13 "1f": 각 쪽 마지막 행에만 붙는다(200행 표본의 100·200행, 짧은 마지막 쪽도 같음). 수정주가 표시가 아니라 쪽 끝 표시로 보인다. 파서는 이 값을 수정 여부로 쓰면 안 된다(공식 의미는 확인 필요).
- C13 보관: SOXX·SOXL·NBIS 모두 2026-04-01 04:00 봉부터다(3/31 조회는 빈 결과). 이동 보관 여부는 11월 초 다시 조회해 확인한다. 서머타임 표기 확인도 2026-11-02 이후.
- C15 대조 원장: 2줄(revision 14→15, 15→16, 둘 다 2026-09-30 UTC, 바깥 변경 없음). 상태 revision 16 = 마지막 apply. 최근 브로커 확인 as_of 2026-09-29라 적용 전 대조를 새로 해야 한다(4일 기준). 원장 이전 revision(≤14)은 원장에 없지만 HWM 시작이 9/30이라 재계산 입력에는 영향 없다.
- C14 계좌 응답 의미(키움 명세 + 조회 전용 1회, 금액은 이 문서에 옮기지 않음)
  - repo 브리지의 체결 조회 `ust21510`은 "당일 주문체결 확인"이라 기간 인자가 없다(X13 원인 확인).
  - 키움에는 기간 조회 API가 따로 있다: `ust21100` 미국주식 거래내역(`overseas accounts transaction-history --from --to --kind`). 거래일, 거래종류(입출금·매매·배당금·환전), 적요(예: "배당금(외화)입금"), 거래금액(외), 수수료(외) `fc_cmsn`, 거래세·외국납부세액, 정산금액(외), 거래 뒤 외화예수금잔고 `fc_entra`를 준다. 7/1~9/30 입출금 종류 조회가 정상 응답했다(배당 입금 1건, 세금 차감과 잔고 포함).
  - 이것으로 "매매로 설명되지 않는 예수금 변화"를 정확히 계산하고 배당·수수료·세금을 입출금과 구분할 수 있다. 다만 `ust21100`은 `kiwoom-broker-readonly-policy.json` 허용 목록에 없다(범위 밖 파일). 그 밖의 기간 API: `ust21150` 일별 주문체결, `ust21132` 특정일 예수금.
  - 매도 직후 `fc_ord_alowa`·`fc_pymn_alowa`·`d1/d2_usd_sell_excta` 변화는 실제 매도가 있어야 관찰할 수 있다(확인 필요, 다음 매도 때 Cowork가 확인).

## 8. 3단계(1차 구현) 지침 (2026-10-01, Cowork)

3절 3~6단계와 Builder 보고 2.2 "1차" 표를 따른다. 결정은 6절, 실측은 7절. 기본값 D1~D12 적용. 아래를 더한다.

1. 범위: 1차만. 기존 키·등록부·고정 파일·범위 밖 파일(`kiwoom-broker-readonly-policy.json`, `kiwoom-readonly-policy.json` 포함)은 건드리지 않는다. `alert_policy.json`은 새 섹션 2개 추가만(status `approved_display_only_old_controls_retained`, policy_version `2026-10-01-s5-r2`).
2. 종가(P3): 시작 시각 표기 기준 정규장 마지막 30분봉(평일 15:30 봉, 조기 폐장일은 `core_close_at` 30분 전 봉)의 종가. 다른 시간대 봉은 버린다. 마지막 행의 `upd_stkpc_tp` "1f"는 쪽 끝 표시라 수정주가 여부로 쓰지 않는다. 출력에 "근사 종가"를 표시한다. 외부 공식 종가가 입력에 있으면 차이만 표시하고 판정에 쓰지 않는다. 새 섹션의 `sox_equivalent.latest_close_bar` 값은 그대로 두고 봉 표기 기준(시작 시각, ET)과 이 결정을 설명 필드로 더한다.
3. V(P4-2): 가용 세션(최소 60)으로 계산하고 "짧은 이력"을 표시한다. 252가 되면 표시를 끈다.
4. 가격 이력(P4-1): `regular_session_close_history.py`는 Cowork가 저장한 키움 CLI 원문 쪽만 읽고 검증한다(쪽 해시, 세션 연속성, 달력 대조, 행 형식). 저장 폴더는 D12. 표본은 7절 경로(절대경로로 읽기)이며, 테스트 픽스처로 쓸 때는 시세 자료만 복사한다.
5. R6(P8-6): 입출금 근거는 `ust21100` 거래내역을 Cowork가 키움 CLI(조회 전용)로 받아 저장한 증거 파일로 넣는다(P4-1과 같은 방식). 브리지·브로커 정책 허용 목록은 바꾸지 않는다. 배당(적요 "배당금")·수수료·세금은 입출금이 아니다. 신고는 대조안 안에 넣어 새 확인 코드를 받는다(1h). 매도 직후 미결제 대금은 확인 전까지 Builder 기본 규칙(다음 대조가 현금을 확인할 때까지 선 판정 보류)을 쓴다. 테스트의 거래내역 픽스처는 가상의 값으로 만들고 실제 계좌 자료를 넣지 않는다.
6. 쓰기 경로: `decision_journal.json` 쓰기는 새 CLI의 확인 코드 경로 하나뿐이다. Claude Code·예약 작업·Judge가 쓰지 못하게 하는 규칙 추가는 병합 뒤 사용자 작업 목록에 적는다(P6 병합 뒤 작업 5).
7. 검증: 3절 4단계 + 2.6(1차는 예상 실패 없음). "새 실패 0"을 지킨다. 커밋하지 않는다.

## 9. S7-1 Judge 판정과 Builder 수정 지시 (2026-10-02)

- 판정: **PASS_WITH_FIXES**(별도 Judge 세션, worktree `s7-policy` 커밋 전 변경, HEAD `08b43a5`). J1·J2·J4·J6·J8·J9·J11 PASS, J3·J5·J10·J12 FIX. 전체 2198개 중 새 미통과 0. 사용자 새 결정 없음. 판정 원문은 사용자가 Cowork에 붙여 넣은 블록(터미널 복사로 일부 줄이 잘림)이고, 아래 필수 수정은 Cowork가 그 블록과 코드(`portfolio_exposure.py:172-190, 905-935`, `portfolio_review_journal.py:115-125`, 분류표)를 대조해 다시 적은 것이다. Judge 세션 재확인 때 원래 판정과 다르면 Judge 쪽이 우선한다.

### 9.1 필수 수정(커밋 전, 같은 Builder). 항목마다 먼저 Judge 재현을 실패 테스트로 만들고 고친 뒤 통과시킨다

| # | 위치 | 문제(Judge 재현) | 고칠 것 |
|---|---|---|---|
| a | `scripts/portfolio_exposure.py:922` | `review_lines.status`가 `HELD`(입출금·매도 보류)일 때 R0가 켜지지 않는다. 보류를 푸는 대조의 `as_of`가 평가 세션보다 늦으면(한국 오후 대조) 선 판정 없이 채우기·신규 매수 표시가 나온다 | `HELD`도 R0(`hwm_line_or_pause_state_missing_or_corrupt` 또는 해당 트리거)로 켠다. 보류 해제는 평가 세션 이전 대조로만 인정하는지 함께 본다 |
| b | `scripts/portfolio_review_journal.py:115`와 적용 시작 후보 계산 | 적용 시작 제안이 `S5_NOT_ACTIVATED`·`JOURNAL_MISSING` 말고 다른 R0를 보지 않는다. 기본 기록 경로면 `non_default_inputs`도 비어, 달력 비ACTIVE·14일 지난 대조·`STATE_CHANGED_OUTSIDE_LEDGER`에서도 `READY`와 확인 코드가 나온다 | 후보 `READY`는 "적용 시작 없음·기록 없음" 외 R0 트리거 0개, 쓰인 종가 전부 확인됨, 대조 나이 4일 이내, 원장 정상, 기본 입력일 때만. 아니면 사유를 달고 `NOT_READY` |
| c | `scripts/portfolio_exposure.py:179`(`common_window`) | 창 안에 종가 하나가 빠지면 창이 그 앞에서 끊겨 252 → 69처럼 줄고 "짧은 이력" 표시만 붙은 채 V가 확인됨으로 나온다 | 가장 이른 가용 세션(보관 시작·상장) 이후 구간의 누락은 V 계산 불가(R0). "짧은 이력"은 가용 이력 자체가 짧을 때만 |
| d | `scripts/run_portfolio_exposure_review.py:250` 부근(평가 세션 결정) | 지금 ACTIVE 달력(8/29까지)에서 기본 실행이 2026-08-28을 최근 완료 세션으로 평가한다(오래된 세션을 최신처럼 보임) | 달력 범위가 실제 최근 완료 세션(오늘 기준)을 덮지 못하면 실패 또는 R0("평가 세션이 최신 아님"). 결과에 평가 세션 날짜를 분명히 표시 |
| e | `scripts/run_portfolio_exposure_review.py:110` 부근(스냅샷 되짚기) | 적용 시작 뒤 revision인데 원장 줄이 없는 스냅샷도 쓰인다. 원장이 없으면 미신고 +$2,000 현금이 HWM에 수익으로 들어가고 `undeclared_cash_flow`가 꺼진다 | 적용 시작 뒤 상태 revision이 원장 줄로 확인되지 않으면 R0. 원장 없음은 적용 시작 뒤에는 통과가 아니다 |
| f | `assets/kiwoom-transaction-history-classification.json` | "수수료출금"이 출금(TRANSFER −), "예탁금이용료입금"이 입금(TRANSFER +)으로 분류된다 | 수수료·세금·이용료(이자) 낱말이 있으면 입출금으로 세지 않는다. 확실하지 않으면 미분류로 멈춘다(fail-closed). 테스트로 두 문자열을 고정 |
| g (Cowork 추가) | `.claude/settings.json` | 새 쓰기 명령 `portfolio_review_journal.py apply`에 deny가 없다(대조 apply에는 있다). Judge는 "적용 시작 전에 끝내면 병합 뒤도 가능"이라 했지만 병합 뒤 사용자 작업을 줄이려고 이번에 넣는다 | 대조 apply와 같은 방식으로 `Bash(*portfolio_review_journal.py apply*)`, `PowerShell(*portfolio_review_journal.py apply*)`와 `stock-strategy-system/decision_journal.json` 직접 편집 deny를 더한다. 제한만 더하고 다른 줄은 바꾸지 않는다 |

### 9.2 병합 뒤 작업에 더할 것(Builder 보고 5.4에 반영, 이번에 구현하지 않음)

1. 순서: `decision_journal.json`·종가·거래내역 증거가 준비되고 U3 실측을 마친 뒤에 "적용 시작"을 기록한다.
2. 확인 기록 마지막 줄 손편집은 사슬로 못 잡는다: 실행마다 다시 계산해 다르면 R0(D28과 같은 규칙, 별도 K2).
3. 거래내역 증거는 원문을 지워 재현이 불가하다: 대조의 예수금 변화와 교차 확인하는 설계(별도). U3 실측은 적용 시작 전.
4. F2(쪽 폴더 이름 = 종목)는 코드로 못 잡으니 절차로 막는다. 100행 쪽을 따로 저장하면 옛 쪽의 첫 봉이 버려지므로(D20) 누적 파일로 저장한다.
5. 결과 스키마 권고 항목의 `additionalProperties`, 세션 불일치 표시, `--earnings` 파일 검증(U7), 분할 처리(U5) — 별도 K2.
6. 배포 때 `rules_hash`가 바뀌어 옛 알림 중복 억제가 한 번 초기화된다(알림이 한 번 더 올 수 있음).

### 9.3 Builder가 할 일

1. 9.1 a~g를 고친다(a~f는 실패 테스트 먼저). 범위(1차, 더하기만)와 3절 절대 규칙은 그대로.
2. 대상 테스트(새 7개 파일 + 고친 곳 관련) → 전체 테스트 서브에이전트 1회, 기준선 대비 새 미통과 0.
3. 보고 파일에 "3.7 Judge 필수 수정 반영"(항목별 재현 테스트 이름, 고친 줄)과 4절 결과 갱신, 5.4에 9.2 추가.
4. 커밋하지 않는다. 마지막 줄 "Builder 수정 완료, worktree s7-policy, 새 실패 수 N".
