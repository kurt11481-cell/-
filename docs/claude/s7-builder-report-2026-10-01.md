# S7 Builder 보고 — S5 확정안 r2 정책 적용 (2026-10-01, K3)

- 상태: **1차 구현·검증 완료 + S7-1 Judge 필수 수정 a~g 반영(3.7절). 커밋하지 않았다.** 다음은 같은 Judge의 재확인이다. 0절 기준선, 1절 조사, 2절 계획, 3절 구현, 4절 검증, 5절 보고. 기존 정책 키·등록부·고정 파일·상태·원장은 고치지 않았다.
- 세션: Claude Code worktree `s7-policy`(브랜치 `worktree-s7-policy`), Opus · xhigh, HEAD `08b43a5`.
- 지시문: `docs/claude/s7-builder-prompt-2026-10-01.md` 3절. 근거: `loss-limit-review-s5-policy-proposal-2026-10-01.md` 확정안 r2, 5절 r2, 9절.
- 경로 표기: `scripts/…`, `tests/…`, `schemas/…`, `references/…`, `assets/…`는 `manage-us-stock-strategy/` 아래다. `파일:줄`은 HEAD `08b43a5` 기준이다.
- 권한: 이 보고의 어떤 내용도 주문·수량 권한을 만들지 않는다(`order_authority=false`, `quantity_authority="none"`, `execution_quantity=null`).

## 0. 기준선

### 0.1 git

- 시작 시 `git status` 깨끗함. HEAD `08b43a5`(= `88f6d4b` 다음 문서 커밋 1개, 예상과 일치).
- 지금 미추적 파일: 이 보고, `docs/claude/s7-builder-baseline-test-failures-2026-10-01.txt`.

### 0.2 정책 파일 해시

| 파일 | 위치 | 원본 sha256 | LF 정규화 sha256 | git blob | 줄바꿈 |
|---|---|---|---|---|---|
| `stock-strategy-system/alert_policy.json` | 원본 폴더 | `184008bd…` | `4a7c1492…` | — | CRLF 783줄 + LF 14줄(혼합) |
| 같음 | worktree | `b8dd1b1a…` | `4a7c1492…` | `3d9df21a…` | CRLF 797줄 |
| `workspace/policies/instrument_registry.json` | 원본 폴더 | `461c2887…` | `8d11aae8…` | — | CRLF 182줄 + LF 26줄(혼합), 끝 줄 LF |
| 같음 | worktree | `f0c2a342…` | `8d11aae8…` | `ade8807f…` | CRLF 208줄 |

- LF 정규화 해시와 blob은 지시문 2절 기준값과 일치한다. 내용은 같다.
- **원본 해시는 worktree에서 재현되지 않는다.** 원본 폴더의 두 파일은 CRLF와 LF가 섞여 있고, worktree는 새 체크아웃이라 전부 CRLF다. 지시문 2절의 "두 파일 모두 CRLF"는 정확하지 않다(혼합).
- 등록부 `canonical_hash`: `750a0b4b…`. `validate_registry_consistency.py` 결과 `VALIDATED`(오류 0, 경고 0).
- `validate_schema_contracts.py`: `PASS`.

### 0.3 고정 파일 정규화 해시 (`validate_skill_deployment.normalized_text_sha256`)

`deployment_gate` 6개 — worktree = 원본 폴더 = 설치 스킬 = `required` = `observed` 모두 일치.

| 이름 | 파일 | 해시(앞 16자) |
|---|---|---|
| timing_engine | `scripts/timing_engine.py` | `DAC71EA7EB5EB2B1` |
| evaluator | `scripts/evaluate_alerts.py` | `66B524857208FF25` |
| skill | `SKILL.md` | `D24D721CD063F4D6` |
| builder | `scripts/build_market_snapshot.py` | `8EF030891559ED60` |
| yfinance_contract | `references/yfinance-data.md` | `32F36475DF864756` |
| output_locale | `assets/locales/ko-KR.json` | `5A0F54DE041A7AAF` |

키움 acceptance 고정 16개 — worktree = 원본 폴더 16개 모두 일치. manifest `f0bab…`의 `implementation_hashes`와는 14개 일치, 2개 불일치(09-29 진단과 같은 기존 상태).

| # | 파일 | 해시(앞 16자) | manifest 일치 |
|---|---|---|---|
| 1 | `schemas/kiwoom-provider-scope.schema.json` | `FFB6BC8E269CF3C1` | 예 |
| 2 | `schemas/kiwoom-session-aware-acceptance-manifest.schema.json` | `4C19DF4C087C572D` | 예 |
| 3 | `schemas/kiwoom-session-aware-priority-policy.schema.json` | `D9983C5DBD27795C` | 예 |
| 4 | `schemas/source-capability.schema.json` | `C191DCAA8E3087EF` | 예 |
| 5 | `scripts/build_kiwoom_market_snapshot.py` | `639A73C89B0A643C` | 예 |
| 6 | `scripts/build_kiwoom_session_observation.py` | `CFD1E7B74E9061E2` | 예 |
| 7 | `scripts/kiwoom_provider_preflight.py` | `DA821A658722B2EA` | 예 |
| 8 | `scripts/kiwoom_runtime_bridge.py` | `61DDF3FDF3843FCD` | 예 |
| 9 | `scripts/materialize_kiwoom_session_aware_acceptance_candidate.py` | `AAFBD4AE51888C27` | 예 |
| 10 | `scripts/run_kiwoom_session_aware_validation.py` | `39504D3FC3A59DB3` | 예 |
| 11 | `scripts/run_manual_portfolio_analysis.py` | `BAEC1640F687FE6B` | 아니오(기존) |
| 12 | `scripts/session_aware_market_data.py` | `1A81DEC666C725F2` | 예 |
| 13 | `scripts/validate_kiwoom_market_snapshot.py` | `3B8301253B8CC853` | 예 |
| 14 | `scripts/validate_kiwoom_session_aware_acceptance.py` | `E9A7962214A8ECCE` | 예 |
| 15 | `scripts/validate_kiwoom_session_aware_acceptance_candidate.py` | `78F1104B73E7EF3E` | 예 |
| 16 | `tests/test_manual_portfolio_analysis.py` | `7368D7C12E3DD934` | 아니오(기존) |

### 0.4 전체 테스트 (서브에이전트 1회)

- 명령: `python -m unittest discover -s manage-us-stock-strategy/tests`, Python 3.13.15.
- 결과: `Ran 2058 tests in 92.899s`, `FAILED (failures=23, errors=291, skipped=1)`. 미통과 314개.
- 지시문 기준선(S4-3 Builder)은 실패 22 + 오류 292 = 314였다. 합계는 같고 구성이 1개 다르다. 원인은 확인하지 않았다(확인 필요). 4단계 대조는 아래 ID 목록으로 한다.
- 실패 ID 목록(314줄): `docs/claude/s7-builder-baseline-test-failures-2026-10-01.txt`.
- 구성: 약 280개가 `IntegratedAuthorityLoadError: INTEGRITY_FAILURE`(worktree 줄바꿈 때문에 원시 해시로 묶인 증거가 달라짐), 29개가 키움 acceptance 해시 불일치, 나머지는 worktree에 없는 미추적 파일·`pypdf` 없음·PowerShell 문제다.
- 모듈별: `test_portfolio_decision_dashboard` 188, `test_integrated_authority_snapshot` 38, `test_portfolio_decision_order_intent` 32, `test_materialize_kiwoom_session_aware_acceptance_candidate` 15, `test_v2_6_7_session_aware_kiwoom_priority` 14, `test_k3_session_calendar_coverage_recovery` 9, `test_sec_scheduled_shadow` 5, `test_manual_portfolio_analysis` 3, `test_nbis_v4_kiwoom_price_authority` 2, 그 밖 8개 모듈 각 1.
- 테스트가 worktree에 남긴 파일 없음.

### 0.5 지시문 2절(Cowork 사전 확인) 재확인

| # | 결과 | 근거 |
|---|---|---|
| C1 | 일치 | `scripts/validate_skill_deployment.py:13-20, 23-26, 36-45` |
| C2 | 일치(16개, 그중 2개는 기존 불일치) | 위 0.3 |
| C3 | repo 경로는 일봉만 읽음: 일치. 일봉 종가에 시간외 값이 섞인다는 점은 문서 근거만 있음 | `scripts/kiwoom_runtime_bridge.py:20-36`, `mvll-holding-card-2026-10-01.md:94-97` |
| C4 | **확인 못 함.** 이 세션에는 키움 명세 조회 도구가 없다. repo 안에 `usa06011`은 한 번도 나오지 않는다 | grep 결과 0건 |
| C5 | **다름.** `portfolio_state.json`이 worktree에 있다(git 무시 대상이지만 worktree 생성 때 복사됨, sha256 `28fd77c5…`로 원본 폴더와 같음). `alert_runtime_state.json`도 있다. 읽기만 했고 쓰지 않았다. "timing_plan을 바꿀 승인된 쓰기 경로가 없다"는 일치 | `scripts/kiwoom_broker_shadow.py:31`, `scripts/apply_user_confirmed_broker_snapshot.py:195-198` |
| C6 | 일치(파일 없음). 단 `.gitignore`에도 없다 | `.gitignore:30-50` |
| C7 | 1d 참고 | — |
| C8 | 일치 | `stock-strategy-system/alert_policy.json:242-292`, `:539` |
| C9 | 일치(원본 폴더에서 읽음). 선례는 `registry_version`과 `required_canonical_sha256`만 바꿨고 캐시는 건드리지 않았다 | `workspace/outputs/lmt-instrument-registry-prod-act/production-policy.patch` |
| C10 | 미실시(Cowork 몫) | — |

## 1. 조사 (읽기만)

### 1.0 먼저 볼 것 — 확정안 r2·지시문과 코드 현실이 어긋나는 곳

2단계 결정 요청으로 올릴 항목이다. 여기서는 사실만 적는다.

| # | 어긋나는 곳 | 근거 | 2단계 |
|---|---|---|---|
| X1 | 상태의 SOXL 타이밍 계획에 완료된 축소 슬롯 `SOXL-R25`와 체결 기록이 있다. 정책에서 슬롯 배열만 비우면 평가기가 `STATE_MISMATCH`(F)로 멈춘다 | `scripts/timing_engine.py:60-65, 101-107`, 상태 구조 확인(1c) | 계획 본문 |
| X2 | 평가기는 "정책의 보유 종목이 모두 실제 보유여야 한다"도 검사한다. S5에서는 SOXL 없음·MVLL 전량 매도가 정상 상태인데, 그 순간 평가기가 F로 멈춘다 | `scripts/evaluate_alerts.py:511-516` | P8 |
| X3 | 신규 매수 승인을 원본 등록부에서만 켜면 `validate_decision_record.py`가 SOXL·NBIS·BE에서 "등록부와 tactical universe 불일치" 오류를 낸다. radar의 승인 게이트는 universe 쪽 값과 AND라 열리지 않는다. MU·DELL·AMD·TQQQ·DRAM은 universe에 없어 두 경로 모두에서 대상이 아니다. universe는 `workspace/policies/` 아래 다른 정책 파일이다 | `scripts/validate_decision_record.py:175-190`, `scripts/run_tactical_opportunity_radar.py:44-46, 266`, `workspace/policies/tactical_candidate_universe.json:23-43` | P8 |
| X4 | `validate_research_packet.py`는 신규 매수 승인을 권한 원본이 아니라 정책 안 캐시에서 읽는다. 캐시에 MU·DELL·AMD·TQQQ 항목을 새로 만들어야 이 게이트가 열린다 | `scripts/validate_research_packet.py:522-538, 587-591` | P8 |
| X5 | 새 종목을 실제로 보유하면 평가기가 캐시의 `identity_status="verified"`, `holding_identity_verified=true`, https 출처를 요구한다. 지금 BE·DRAM 캐시 항목은 둘 다 없다. 지시문의 신원 확인 목록은 MU·DELL·AMD·TQQQ뿐이다 | `scripts/evaluate_alerts.py:518-530`, `scripts/build_holding_strategy_review.py:163-167`, `alert_policy.json:218-240` | P8 |
| X6 | 30분봉(`usa06011`)을 읽는 경로가 repo에 없다. 만들려면 acceptance 고정 파일 `kiwoom_runtime_bridge.py`와 다른 정책 파일 `kiwoom-readonly-policy.json`을 고쳐야 한다. 둘 다 승인 범위 밖이다 | `scripts/kiwoom_runtime_bridge.py:20-36, 107-112`, `workspace/policies/kiwoom-readonly-policy.json:14-22` | P4 |
| X7 | `decision_journal.json` 경로는 이미 다른 설계(P3·P4의 카드 결정 원장)가 쓰기로 정했고, `portfolio_status.py`가 그 형식(`entries`, `outcome`)을 가정해 읽는다. `tactical_radar_policy.json`은 예약 radar가 "decision_journal"을 쓸 수 있다고 적는다. S5의 "사용자 확인으로만 쓴다"와 충돌한다 | `scripts/portfolio_status.py:35, 201-211`, `workspace/policies/tactical_radar_policy.json:13`, `system-review-p4-roadmap-2026-09-30.md:465` | P1 |
| X8 | 현황판(`portfolio_decision_dashboard.py`)에는 사용자 승인 위험 한도표가 따로 있다: 전체 레버리지 조정 노출 목표 90~110%·상한 125%, 현금 하한 10%, 3배 ETF 상한 10%. S5(목표 1.55, 현금 하한 없음)와 반대다. S5 제안서에 이 파일 언급이 없다 | `assets/portfolio-decision-risk-envelope-v0.2.json:7-11, 17-21, 38-42`, `scripts/portfolio_decision_dashboard.py:1075-1133` | P8 |
| X9 | 카드 검증기는 `target_weight_pct`와 "target + weight" 조합 키를 주문 필드로 보고 거부한다. S5 권고 출력은 "목표 비중"이다. 권고는 카드 JSON에 넣을 수 없다 | `scripts/validate_holding_card.py:30-36, 57-62` | 계획 본문 |
| X10 | `timing_engine.py`·`evaluate_alerts.py`를 고치면 `test_v2_6_integration`이 실패한다. 이 테스트는 설치 스킬 폴더를 직접 읽어 원본 = 설치를 요구한다. 설치 폴더는 Builder가 쓸 수 없다. "새 실패 0개"와 양립하지 않는다 | `tests/test_v2_6_integration.py:68`, `tests/test_v2_4_automation.py:54-71` | P5 |
| X11 | 현황판 테스트 306개 중 188개가 worktree 기준선에서 이미 오류다. 현황판을 고치면 이 worktree에서 검증할 수 없다 | 0.4 | 계획 본문 |
| X12 | gap 감시 식은 기술 손절선을 쓰고, 그 손절선에 원가 한도 경계가 들어 있다. 원가 한도를 내리면 gap 감시의 한 항이 바뀐다 | `scripts/timing_engine.py:141-170, 205-221`, `alert_policy.json:480, 570` | P8 |
| X13 | R6의 "매매로 설명되지 않는 예수금 변화"를 계산할 입력이 부족하다. 체결 조회에 기간 인자와 수수료·세금 필드가 없다 | `scripts/kiwoom_account_readonly_bridge.py:33, 51-54` | P8 |
| X14 | MU·DELL·AMD·TQQQ는 Production 신원 권한 범위에도, 키움 시세 승인 범위에도 없다(DRAM은 신원 범위에만 있다). 등록부에서 승인해도 수동 분석·시세 경로에서는 `UNKNOWN_SYMBOL`·미승인 종목이다. 두 파일 모두 이번 범위 밖이다 | `workspace/policies/integrated_identity_session_activation.json:15-30`, `scripts/instrument_identity_authority.py:150-153`, `workspace/policies/kiwoom-session-aware-priority-policy.json:83-97` | P8 |
| X15 | `holding_risk_rules`·`holding_timing_rules`가 바뀌면 통합 shadow cohort 지문이 바뀐다. 기대값은 추적 파일 `workspace/state/integrated_shadow/shadow_progress.json`에 있고 테스트 1개가 저장값 = 재계산값을 요구한다. 맞추려면 이 상태 파일을 이관 스크립트로 다시 써야 한다(지시문의 금지 목록에는 없지만 상태 파일이다) | `scripts/shadow_acceptance.py:211-229`, `scripts/migrate_integrated_shadow_cohort.py:32-68`, `tests/test_v2_6_7_session_aware_kiwoom_priority.py:505-515` | P8 |
| X16 | "기존 규칙 불변"을 단언하는 테스트가 여럿 있다(원가 한도 0.2·0.6·0.1, 슬롯 수량, 재무장 값). 이번 변경은 이 불변식을 의도적으로 깬다. 테스트를 고치면 그 테스트가 증명하던 내용이 바뀐다 | `tests/test_v2_6_12_holding_valuation_shadow.py:389-401`, `tests/test_v2_5_leveraged_confirmation.py:50`, `tests/test_v2_6_3_free_web_new_buy.py:222-228`, `tests/test_v2_6_integration.py:63` | 계획 본문, Judge 확인 |

### 1a. 바꿔야 할 파일, 고정 여부, K 등급 (최소 집합 제안)

고정 표기: **G** = `deployment_gate` 6, **A** = acceptance 16, 없음 = 비고정.

| 파일 | 고정 | K | 이유 | 판단 |
|---|---|---|---|---|
| `stock-strategy-system/alert_policy.json` | — | K3 | 5절 r2 전부, `deployment_gate` 해시 | 필수 |
| `workspace/policies/instrument_registry.json` | — | K3 | #12 | 필수 |
| `scripts/timing_engine.py` | **G** | K3 | 은퇴 슬롯 무시, 슬롯 없이 gap·halt 감시(X1) | 필수 |
| `scripts/evaluate_alerts.py` | **G** | K3 | 원가 한도 판정 제거, 타이밍 호출부(1b·1c) | 필수 |
| `scripts/validate_research_packet.py` | — | K2 | 원가 한도가 없으면 모든 패킷이 `rejected`(1b) | 필수 |
| `scripts/build_holding_fact_pack.py` | — | K2 | 원가 한도 칸 처리, 표시 한 줄 입력 | 필수 |
| 새 계산 모듈 + 새 스키마 + 새 locale + 새 테스트 | — | K3 | R0~R6, R9 계산 | 필수(ADD) |
| `scripts/render_holding_cards.py`, `assets/locales/holding-card-ko-KR.json` | — | K1 | 표시 한 줄 | 필수 |
| `scripts/portfolio_status.py`, `assets/locales/portfolio-status-ko-KR.json` | — | K1 | 표시 한 줄 | 선택(1j) |
| `scripts/reconcile_broker_state.py`, `scripts/kiwoom_broker_shadow.py`, `scripts/apply_user_confirmed_broker_snapshot.py`, `schemas/kiwoom-reconciliation-proposal.schema.json`, `assets/locales/reconcile-broker-state-ko-KR.json` | — | K3 | R6 신고(apply 경로) | 계획에 있을 때 |
| `.gitignore` | — | K1 | `decision_journal.json` 등 새 원장 무시 | 필수 |
| 기존 테스트(1k), `tests/fixtures/decision-record.valid.test-only.json` | — | K2 | 정책·엔진 변경 반영 | 필수 |
| `workspace/state/integrated_shadow/shadow_progress.json` + 새 보관 파일 1개 | — | K2 | cohort 이관(X15). 카운터가 모두 0이라 잃는 기록은 없다 | **결정 필요** |
| `references/*.md`, `stock-strategy-system/*PROMPT*.md` | — | K0 | 원가 한도·슬롯 설명 111곳(21개 파일) | 병합 뒤 정리 가능 |
| `scripts/portfolio_decision_dashboard.py` | — | K2 | 원가 한도 값을 지우면 `:517-518`에서 KeyError | **고치지 않는 쪽 제안**(X11). 조건은 1b |
| `scripts/portfolio_policy_gates.py`, `scripts/audit_hard_risk_policy.py`, `scripts/shadow_acceptance.py` | — | — | 값이 없으면 스스로 `UNVERIFIED`·해시 변경으로 처리 | NO_CHANGE |
| `SKILL.md`, `assets/locales/ko-KR.json` | **G** | — | 원가 한도·슬롯 문구가 본문에 없음(`SKILL.md:37, 41`은 참조 문서 안내). 새 문구는 비고정 locale에 둔다 | NO_CHANGE |
| `scripts/build_market_snapshot.py`, `references/yfinance-data.md` | **G** | — | 금지 | NO_CHANGE |
| acceptance 16개 | **A** | — | `run_manual_portfolio_analysis.py`는 `holding_risk_rules`·타이밍 규칙을 읽지 않는다(grep 1건, `:180` `hard_risk_authority`뿐) | NO_CHANGE |
| `workspace/policies/tactical_candidate_universe.json` | — | K3 | X3 | **범위 밖, 결정 필요** |
| `scripts/kiwoom_runtime_bridge.py`(**A**), `workspace/policies/kiwoom-readonly-policy.json` | **A** | K3 | X6 | **범위 밖, 결정 필요** |
| `assets/portfolio-decision-risk-envelope-v0.2.json` | — | K3 | X8 | **범위 밖, 결정 필요** |

### 1b. `holding_risk_rules`를 읽는 8개 스크립트 — 원가 한도를 내리면 생기는 동작

| 스크립트 | 지금 하는 일 | 원가 한도 값을 지우면 | 종목 항목까지 지우면 |
|---|---|---|---|
| `evaluate_alerts.py` **G** | 보유 등록부 검사 3종(`:489-493` 비어 있으면 오류, `:499-509` 보유 ⊆ positions ∪ de_minimis, `:511-516` positions ⊆ 보유). 한도 값 검사(`:539-541`). 종목마다 `holding_max_loss_breach` 후보, 위반이면 D(`:763-833`). 타이밍 호출에 한도 경계 전달(`:900-903`). D가 하나라도 있으면 `risk_freeze_active`(`:1005-1007`) | `STATE_MISMATCH` F("invalid maximum-loss fraction"). 검사를 빼도 `:767`, `:902`에서 KeyError | `STATE_MISMATCH` F("holding risk position rules are missing" 또는 "neither a holding-risk rule nor…") |
| `validate_research_packet.py` | 보유 레버리지 ETF가 positions에 없으면 오류(`:609-612`). 종목마다 유효한 한도 요구(`:640-642`). 위반 + freeze면 매수 hard gate(`:647-653`) | 모든 패킷 `rejected`·F("has no valid loss rule") | SOXL·MVLL 보유 중 모든 패킷 `rejected` |
| `reconcile_broker_state.py` | positions·de_minimis로 `POLICY_POSITIONS_MISMATCH` 경고 계산, 평가기 무결성 검사 호출(`:60-79`) | 대조안의 적용 후 검사 `FAIL` 경고 | 같음 |
| `portfolio_decision_dashboard.py` | 키움 전용 대체 경로에서 한도 값으로 경계 계산(`:517-518`) | 그 경로에 들어가면 KeyError(잡는 곳 없음) | 같음 |
| `build_holding_fact_pack.py` | 원가 한도 칸(`:190-250`), 기본 방향으로 규칙 방향 결정(`:270-282`), 카드 숫자 `loss_limit_*`(`:401-402`) | `NOT_EVALUATED`·`BOUNDARY_INPUT_INVALID`, 누락 코드 `LOSS_LIMIT_NOT_EVALUATED` | `NO_POLICY_RULE`, 규칙 방향 `NONE` |
| `portfolio_policy_gates.py` | 규칙 출처 감사(`:97-132`) | `provenance_complete` 거짓 → 권한 상태 미확인 | 같음 |
| `audit_hard_risk_policy.py` | 위 감사를 종목별로 모음(`:15-32`) | 전체 상태가 `VERIFIED`가 아님 | 규칙 0개 |
| `shadow_acceptance.py` | `holding_risk_rules`·`holding_timing_rules`로 의미 해시(`:223-229`) | 해시 변경(1d) | 같음 |

- **등록부 역할**: `holding_risk_rules.positions`의 키 집합이 "지금 보유해야 하는 종목 목록"으로 쓰인다(평가기 `:499-516`, 대조 `:67-72`, 패킷 검증기 `:609`). 원가 한도 값과 등록부 역할이 한 항목에 묶여 있다.
- **freeze 기본값**: 키가 없으면 `True`다(`scripts/validate_research_packet.py:648-651`, 옛 이름 `freeze_new_buys_on_any_breach`도 본다). r2대로 `false`를 명시해야 한다. 원가 한도 판정이 없어지면 `risk_breaches`가 항상 비므로 이 gate는 어차피 발동하지 않는다.
- **D 등급 경로**: D를 만드는 곳은 원가 한도 위반 하나뿐이다(`scripts/evaluate_alerts.py:819`). 내리면 평가기에서 D와 `HARD_RISK_REVIEW`(`:1013-1015`)가 나오지 않는다. `alert_grades.D` 설명(`alert_policy.json:699`)은 "maximum-loss boundary"로 적혀 있다. 하류의 `build_holding_strategy_review.py:204-224`(hard-risk 분기)는 후보가 없으면 그냥 지나간다.
- **de minimis**: 상태에 NBIL 보유가 없다(보유 종목 MVLL·NBIS·SOXL). `de_minimis_manual_exit_positions.NBIL` 삭제(#3)는 평가기 검사에 걸리지 않는다. `de_minimis`가 빈 dict여도 통과한다(`:494-497`).
- **`rules_hash`**: 정책 전체(보관 전략 제외)로 만든다(`scripts/evaluate_alerts.py:227-233`). 정책이 바뀌면 모든 `event_key`가 바뀌어 중복 억제가 한 번 초기화된다(기존 동작).

### 1c. `timing_engine.py` — 슬롯 은퇴와 상태의 `timing_plan`

- 열린 슬롯이 없으면 gap·halt 감시도 나오지 않는다: `_next_open_slot`이 `None`이면 `return None, []`(`scripts/timing_engine.py:412-414`). 감시 판정(`:430-459`)은 그 뒤에 있다.
- 상태 확인(값은 출력하지 않고 구조만):
  - `timing_plan.policy_version`은 정책과 같다.
  - SOXL: `completed_tranche_ids = ["SOXL-R25"]`, 체결 기록 1건, 보유 = anchor − 24주(일치).
  - MVLL: 완료 슬롯 없음, 보유 = anchor(일치).
  - 지금 정책으로 `leveraged_state_integrity_errors`는 오류 0개다.
- 슬롯 배열을 비우면(5절 #4·#5 문자 그대로):
  - SOXL: "unknown completed timing tranche(s): ['SOXL-R25']"(`:60-65`).
  - 이 검사를 지나도 "holdings do not equal anchor less confirmed tranches"(`:101-107`). 슬롯이 없으면 매도 합계가 0이라 보유 = anchor여야 하는데 SOXL은 다르다.
  - 둘 다 `STATE_MISMATCH` F로 이어진다(`scripts/evaluate_alerts.py:583, 741-747`).
- 은퇴 뒤 사용자가 SOXL·MVLL을 수동으로 줄이면 anchor 등식이 영구히 깨진다. 슬롯·체결 기록 경로가 없어 다시 맞출 방법이 없다.
- `holding_timing_rules.policy_version`을 바꾸면 상태의 `timing_plan.policy_version`과 달라져 F다(`:39-41`). 상태 쓰기 경로가 없으므로 이 값은 그대로 둬야 한다.
- **상태 쓰기 없이 처리 가능한가: 가능하다. 엔진 수정이 전제다.** 은퇴한 종목은 (a) anchor·슬롯 검사를 건너뛰고(`timing_anchor_errors`), (b) 슬롯 없이 gap·halt만 평가하고(`evaluate_holding_timing`), (c) 상태의 `timing_plan.positions.<종목>`은 읽지 않는다. 상태에는 옛 계획이 그대로 남는다(읽히지 않는 이력).
- 엔진에서 같이 손봐야 하는 곳: `event_key`가 슬롯 ID와 `anchor_id`를 쓴다(`:465-475`), 수량을 슬롯에서 읽는다(`:476`), 감시 우선순위에 `weakness_10ema`가 있다(`:385`), 재무장 평가(`:421-429`).
- 평가기 쪽: 타이밍 호출이 원가 한도 경계를 넘긴다(`scripts/evaluate_alerts.py:900-903`). 이 값은 기술 손절선(`timing_engine.py:158-162`)을 거쳐 gap 판정의 "전일 손절선을 뚫는 시가"(`:214-216`)에 들어간다(X12).
- 대조 쪽: 상태의 `timing_plan.positions`에 있는 종목 수량이 바뀌면 `TIMING_PLAN_TICKER_CHANGED` 경고가 붙는다(`scripts/kiwoom_broker_shadow.py:346-348`). 은퇴 뒤에도 상태가 남아 있어 경고는 계속 뜬다. 안내문(`references/broker-snapshot-reconciliation.md:117-121`)의 "체결 확인 전까지 STATE_MISMATCH"는 더 이상 맞지 않게 된다.
- 현황판의 수동 타이밍 투영은 `holding_timing_review`·`reduce` 이벤트만 쓴다(`scripts/portfolio_decision_dashboard.py:418-420, 528-533`). 은퇴 뒤에는 결과가 비게 된다(오류 아님).
- 카드 fact pack의 타이밍 칸도 `holding_timing_review`만 찾는다(`scripts/build_holding_fact_pack.py:261-267`). 은퇴 뒤 `NOT_EVALUATED`·`NO_TIMING_CANDIDATE_IN_ALERT_RESULT`가 된다.

### 1d. 정책·등록부 변경이 닿는 곳

서브에이전트가 조사했고, 판단에 쓰는 줄은 Builder가 직접 다시 읽었다. 예약 런타임 clone 안의 내용은 서브에이전트 읽기 결과다(직접 확인 안 함).

| 대상 | 무엇에 묶이나 | 해시 기준 | 이번 변경의 영향 |
|---|---|---|---|
| 배포 provenance | 스크립트 3개 + 정책 4개. `alert_policy.json` 포함, 등록부는 미포함(`scripts/run_deployment_provenance.py:26-34`) | **원시 바이트**(`scripts/deployment_provenance.py:17-18`) | manifest는 이 repo에 없고 예약 런타임 clone(`main`, `41f7b3f`)의 `workspace/outputs/activation/deployment-provenance/current.json`에 있다. 이 브랜치 병합만으로는 영향 없음. `main` 반영·런타임 배포 때 `CURRENT_HASH_MISMATCH`(`:163-164`)가 나고 manifest를 다시 만들어야 한다 |
| 예약 경로 `verify_current_provenance` | HEAD·깨끗한 작업 폴더·`main` 브랜치·파일 해시·cohort(`:126-201`) | 원시 바이트 | 코드에서 부르는 곳은 `scripts/run_manual_portfolio_analysis.py:2211-2236` 하나다(실패 시 `SCHEDULED_DEPLOYMENT_NOT_VERIFIED`). 그 밖의 예약 작업은 지시문(프롬프트)으로 gate를 건다 |
| `shadow_acceptance.py` 의미 해시 | `strategy_version` + `holding_risk_rules` + `holding_timing_rules`(`:223-229`). 등록부는 MVLL·SOXL의 `research_instrument_type`·`confirmation_mode`·`confirmation_proxy`만(`:233-240`). 파일 목록(`:27-78`)에 `kiwoom-readonly-policy.json` 포함 | 정규화 JSON | #1~#8·#14가 들어가면 지문이 바뀐다(X15). 등록부 변경(#12), `decision_harness`, 새 섹션 2개, 최상위 `policy_version`은 영향 없음 |
| `shadow_acceptance_policy.json` `required_baseline_tickers` | 읽는 코드 없음. 코드는 상수를 쓴다(`scripts/shadow_acceptance.py:26`) | — | 영향 없음. 슬롯을 은퇴해도 shadow의 NBIS·MVLL·SOXL baseline 요구는 그대로다 |
| `event_risk_policy.json` `source_policy` | 문자열 표기뿐 | — | 영향 없음 |
| `mvll-volume-authority-policy.json` | `holding_timing_rules.definitions.pullback_reclaim_relative_volume_minimum`을 읽는다(`scripts/validate_mvll_volume_authority.py:49`) | 값 | r2는 `definitions`를 건드리지 않는다. 남겨야 한다(지우면 KeyError) |
| `integrated_identity_session_activation.json` | 자기 신원 artifact의 해시(`:12`). `alert_policy.json`·등록부 해시는 없다 | 원시 바이트(다른 파일) | 영향 없음. 범위 문제는 X14 |
| 수동 CA 확인 영수증 | 정책 전체 해시(`scripts/validate_technical_snapshot.py:286-289`) | 정규화 JSON | 지금 영수증 목록이 비어 있어(`alert_policy.json:414`) 영향 없음. 앞으로 받는 영수증은 새 정책 해시에 묶인다 |
| 기록만 하는 곳 | `portfolio_decision_dashboard.py:2502-2511`, `point_in_time_context.py:154`, `run_llm_decision_stability.py:213`, `build_run_manifest.py`(orchestrator `:395`) | 원시 바이트 | 기록값이 달라질 뿐 비교하는 곳 없음 |

버전 문자열:

| 값 | 비교하는 곳 | 올리면 |
|---|---|---|
| `strategy_version`(`alert_policy.json:3`) | 상태와 일치 요구(`scripts/evaluate_alerts.py:446-447`), `portfolio_policy_gates.py:45`, 테스트 고정값 | `STATE_MISMATCH` F. 상태 쓰기 없이는 올릴 수 없다 |
| `holding_timing_rules.policy_version`(`:417`) | 상태 `timing_plan.policy_version`(`scripts/timing_engine.py:39-41`) | F. 올릴 수 없다 |
| 최상위 `policy_version`(`:4`) | 읽는 곳 없음 | `rules_hash`만 바뀜 |
| `holding_risk_rules.rule_version`(`:330`) | 이벤트 키 재료(`scripts/evaluate_alerts.py:759, 785-793`) | 이벤트 키 변경 |
| 등록부 `registry_version` | 결정 기록과 일치 요구(`scripts/validate_decision_record.py:198-199`), 테스트 픽스처 | 옛 기록·픽스처 불일치 |

- 현재 해시 문자열을 담은 추적 파일은 `alert_policy.json:177`과 `docs/claude/` 메모뿐이다(테스트·픽스처·다른 정책에는 없음).
- 줄바꿈(예상, 확인 필요): 병합으로 두 정책 파일이 바뀌면 원본 폴더에서 git이 파일을 CRLF로 다시 쓴다. 지금의 혼합 줄바꿈 원시 해시(`184008bd…`, `461c2887…`)는 내용과 무관하게 달라진다. 원시 바이트에 묶인 것은 위 배포 provenance(런타임 clone)뿐이다.

### 1e. 상품 등록

- **원본 형식**: `workspace/policies/instrument_registry.json`의 `instruments.<TICKER>`. 두 가지 모양이 섞여 있다.
  - 1차 출처형(TOST·NOW·FSLY·LMT, `:109-174, 185-206`): `legal_issuer_name`, `instrument_type`, `security_class`, `exchange`, `trading_currency`, `identity_status="verified_primary_source"`, `identity_verification_status="VERIFIED"`, `official_identity_source_url`(SEC 10-K), `official_identity_source_type="SEC_10_K"`, `identity_verified_at`, `leverage_factor`, `leverage_factor_status`, `confirmation_proxy`, `watchlist_approved`, `new_buy_instrument_approved`, `short_sale_approved`, `candidate_status`, `portfolio_bucket`, `theme`, `subtheme`.
  - 기존 정책형(MVLL·SOXL·NBIS·BE·NBIL·DRAM): `identity_status="verified_by_existing_active_policy"`, 출처 URL 없음. 레버리지 상품은 `research_instrument_type`, `confirmation_role`, `confirmation_mode`, `daily_target_multiple`가 더 있다(`:14-50`).
  - 등록부 스키마 파일은 없다(필드 이름을 검사하는 코드 없음).
- **`canonical_hash`**: 키 정렬·공백 없는 JSON의 sha256(`scripts/validation_common.py:35-37`). 줄바꿈·키 순서·들여쓰기와 무관하다.
- **고정과 캐시**: `required_canonical_sha256`(`alert_policy.json:177`)이 원본 해시와 같아야 한다. 캐시(`:183-241`, 6개)는 원본에 있는 종목에 한해 `instrument_type`, `watchlist_approved`, `new_buy_instrument_approved` 3개 필드가 같아야 한다(`scripts/validate_registry_consistency.py:14-18, 38-50`). 캐시에만 있는 종목은 경고다. 캐시와 원본은 필드 구성이 다르다(캐시는 `official_issuer`, `official_identity_source_url`, `holding_identity_verified` 등). "동기화"는 통째 복사가 아니라 이 3개 필드 맞춤이다.
- **`new_buy_instrument_approved`를 읽는 곳**

| 스크립트 | 읽는 원천 | 동작 |
|---|---|---|
| `validate_research_packet.py:522-538, 587-591` | **캐시** | 캐시에 종목이 없으면 hard gate "not present in the deterministic policy registry". `identity_status != "verified"`면 hard gate. 승인 값이 true가 아니면 매수 hard gate |
| `validate_decision_record.py:168-190, 273-282` | 원본 + universe | universe에 종목이 없으면 오류. 원본 `new_buy_instrument_approved` ≠ universe `new_buy_approved`면 **오류**(X3) |
| `run_tactical_opportunity_radar.py:44-46, 266, 283-288` | 원본 + universe | 대상 종목은 universe의 `candidate_status="active"`·`watchlist_approved`. 승인 = universe 값 AND 원본 값 |
| `screen_tactical_candidates.py:65, 94` | 원본 + universe | 위와 같은 AND |
| `build_new_buy_strategy_draft.py:54-56` | 입력 context | false면 `INSTRUMENT_APPROVAL_PENDING`. 출력은 항상 `quantity=None`, `quantity_authority="none"`(`:105`) |
| `validate_new_buy_strategy_draft.py:24`, `build_new_buy_approval_proposal.py:20` | 초안 값 | 같은 값 재검사 |

- **승인 값 외 필드가 게이트에 주는 영향**
  - 원본의 `candidate_status`(DRAM `reference_only`)는 스크립트가 읽지 않는다. radar가 읽는 `candidate_status`는 universe 쪽이다(`run_tactical_opportunity_radar.py:44-46`). 테스트 1곳이 원본 값을 본다(`tests/test_v2_2_tactical_radar.py:75-85`).
  - 원본의 `identity_status`: radar `:238, 255`, `validate_decision_record.py:274`, `build_holding_strategy_review.py:163`이 "미검증 값 목록"에 있는지만 본다.
  - 원본의 `leverage_factor`·`leverage_factor_status`: 현황판이 `verified` 또는 `verified_by_existing_active_policy`만 받는다(`portfolio_decision_dashboard.py:1031-1035`). `theme`은 반도체 묶음 판정에 쓴다(`:1040-1042`).
  - `registry_version`: 결정 기록의 값과 같아야 한다(`validate_decision_record.py:198-199`). 올리면 옛 결정 기록은 버전 불일치가 된다(새 기록은 새 값).
- **캐시 쪽 신원 필드**(X5): 보유 종목마다 `identity_status="verified"`, `holding_identity_verified=true`, https `official_identity_source_url`이 필요하다(`evaluate_alerts.py:518-530`). 지금 캐시에서 BE·DRAM은 `holding_identity_verified=false`이고 URL이 없다.
- **1차 출처 확인**: MU·DELL·AMD(SEC 10-K), TQQQ(ProShares Trust 투자설명서)는 3a에서 한다. 이번 단계에서는 sec.gov에 접속하지 않았다.

### 1f. `approved_rule_registry`

- 형식: `rule_id → {status, symbol | symbols, allowed_actions, quantity_authority, authority}`(`alert_policy.json:242-292`).
- 검증기 규칙(`scripts/validate_research_packet.py:540-570`): hold·watch가 아닌 제안은
  - 규칙이 dict가 아니면 hard gate,
  - `status != "approved"`면 hard gate "not approved",
  - `rule.symbol != 제안 종목`이면 **오류**(`symbols` 목록은 인정하지 않는다),
  - 제안 행동이 `allowed_actions`에 없으면 오류,
  - `quantity_authority`가 `none`·`fixed`가 아니면 오류, `none`이면 hard gate "authorizes review but no trade quantity".
- 행동 어휘: `buy`, `sell`, `reduce`, `hold`, `watch`(`:31`). 수량 권한 어휘: `none`, `fixed`(`:42`).
- 지금 7개 중 검증기를 "approved"로 통과하는 것은 `soxl_max_loss_review`, `mvll_max_loss_review` 둘뿐이다. 나머지는 status가 `approved`가 아니거나(`approved_review_only` 등), 행동이 어휘 밖이거나(`risk_review`, `manual_exit_review`, `gate_next_weakness_review`), 수량 권한이 어휘 밖이다(`versioned_anchor_and_shared_tranche_slots`).
- 규칙 ID는 정책 파일 밖 어디에서도 참조되지 않는다(스크립트·테스트 grep 0건).
- **은퇴 표시 방법**: 항목을 남기고 `status`를 `approved`가 아닌 값으로 바꾸면 검증기가 hard gate로 막는다. 코드 수정이 필요 없다(`validate_research_packet.py` 무변경).
- **S5 규칙 등록**: 종목마다 한 항목이어야 한다(`symbol` 일치). 줄이기는 `allowed_actions ["reduce","sell"]`, 채우기는 `["buy"]`, 둘 다 `status "approved"`, `quantity_authority "none"`. 이렇게 등록해도 hard gate 두 개("no trade quantity", 수량 미제공)가 남아 결과는 `watch_only`·B 이하다(`:515-516, 557-558, 660-662`). 패킷은 후보를 만들지 않는다(`:684-685`).

### 1g. V 가격 이력 (요구 9)

- repo의 키움 시세 경로는 `kiwoom_runtime_bridge.py` 하나이고 허용 대상은 6개 API다. 차트는 `daily_chart`(`usa06012`)뿐이다(`:20-36`). 목록 밖 API는 `blocked_api_target`이 막는다(`:107-112`).
- 승인 정책도 같다: `allowed_operations`, `allowed_api_targets`에 `usa06011`이 없다(`workspace/policies/kiwoom-readonly-policy.json:14-22`).
- 스키마도 일봉 고정이다(`schemas/kiwoom-market-series.schema.json:39, 54`).
- **결론: 고정 파일을 건드리지 않고 `usa06011` 30분봉 252세션 이력을 얻는 경로는 repo에 없다.** 새 브리지를 따로 만들어도 `kiwoom-readonly-policy.json` 허용 목록 변경(다른 정책 파일)이 필요하다.
- r2는 이 경우를 정해 두었다: 정규장 종가 이력을 얻지 못하면 V 계산 불가 → R0(`sox_equivalent.regular_session_history_unavailable = "exposure_unavailable"`). R4 자산도 같은 종가를 쓰므로 선 판정·R5 고점도 같이 "미확인"이 된다.
- `cntr_tm` 시각대, 수정주가(`upd_stkpc_tp`) 동작, 연속조회, 이력 깊이: **확인 필요**(이 세션에서 명세를 조회할 수 없다). 참고로 Cowork 수동 점검 기록은 "시각은 ET, 봉 시작 시각 표기"다(`mvll-holding-card-2026-10-01.md:95`). 일봉 쪽은 RAW `upd_stkpc_tp=0`, 수정 `=1`이다(`kiwoom_runtime_bridge.py:244`, `kiwoom-readonly-policy.json:27-28`).
- 16:00 표기 봉에 대한 주의(확인 필요): 봉 시작 시각 표기라면 16:00 봉은 16:00 이후 구간이다. 마감 동시호가 체결이 들어가지만 그 뒤 시간외 체결이 섞이는지는 명세·실측으로 확인해야 한다. 같은 날 MVLL 15:30 봉 종가($35.83)와 16:00 봉 종가($35.81)가 달랐다(`mvll-holding-card-2026-10-01.md:95`).
- 조기 폐장일: 세션 달력 권한이 세션별 `core_close_at`을 준다(`scripts/session_authority.py:44, 131`). 폐장 직전 봉은 이 값으로 고를 수 있다. 다만 worktree에서는 달력 artifact가 무결성 오류라(0.4) 새 테스트는 픽스처를 써야 한다.
- 규모 참고: 252세션 × 13봉 = 종목당 3,276봉, 대상 10종목(등록 상품 9 + SOXX).

### 1h. `reconcile_broker_state.py` — R6 신고 자리와 미결제 매도 대금

- 대조안 형식은 `additionalProperties: false`다(`schemas/kiwoom-reconciliation-proposal.schema.json`). 버전 `kiwoom-reconciliation-1.0`은 apply 라이브러리에 고정돼 있다(`scripts/apply_user_confirmed_broker_snapshot.py:25, 217-225`). 신고 필드를 넣으려면 스키마와 버전이 함께 바뀐다.
- `proposal_id` = `proposal_id`·`confirm_code`를 뺀 대조안 전체의 해시, 확인 코드 = 그 앞 8자(`scripts/kiwoom_broker_shadow.py:244-246, 423-424`). 신고가 대조안 안에 있으면 자동으로 "신고 뒤 새 코드"가 된다. apply는 해시를 다시 계산해 대조한다(`apply_user_confirmed_broker_snapshot.py:259-261`).
- 원장 한 줄에는 `changes`, 확인 코드, 사용자 메시지, 전후 해시가 남는다(`:299-316`). 신고를 원장에 남기려면 여기에 필드를 더한다.
- 상태에 쓰는 필드는 5개다: `holdings`, `average_cost_usd`, `position_cost_basis_usd`, `aggregate_cost_basis_usd`, `available_cash_usd`(`kiwoom_broker_shadow.py:29-30`). 그 밖은 `NEVER_TOUCHED`(`:31`)이고 apply가 바뀌지 않았는지 검사한다(`apply_user_confirmed_broker_snapshot.py:195-198`). 신고를 상태에 넣으면 이 목록이 바뀐다.
- **들어갈 자리(구조상)**: `propose` → 신고 입력 → 대조안에 `cash_flow_declaration` 포함 → `show` 표에 표시 → `확인 <새 코드>` → apply가 원장에 기록. 바뀌는 파일은 1a의 R6 줄 5개다.
- **신고 한도 계산 입력**
  - 예수금: `fc_entra`(외화 예수금), `fc_pymn_alowa`(출금 가능), `fc_ord_alowa`(주문 가능)(`scripts/kiwoom_account_readonly_bridge.py:37`).
  - 체결: `cntr_qty`, `cntr_uv`, `slby_tp`, 시각(`:51-54`). 수수료·세금 필드 없음. 조회 본문에 기간 인자 없음(`:33`). 며칠 치가 오는지 **확인 필요**.
  - 입출금·배당 내역을 주는 조회는 계정 브리지에 없다(`:20-27`).
  - 따라서 "매매로 설명되지 않는 예수금 변화"는 수수료·세금·배당이 섞인 값으로만 나온다. 대조 간격이 하루를 넘으면 체결 누락 가능성이 있다(X13).
- **미결제 매도 대금**
  - 상태의 현금은 min(출금 가능, 주문 가능)이고 "미결제 미포함"으로 고정돼 있다(`kiwoom_broker_shadow.py:75-77, 333, 390-394`).
  - 미결제 금액(`d1/d2_usd_sell_excta` 등)은 대조 스냅샷에는 있지만(`:78-84`) 표시 전용 조회에서 오고(`:28`) 상태에 쓰지 않는다.
  - 매도 직후 상태만으로 자산을 계산하면 보유는 줄고 현금은 아직 안 늘어, 자산이 매도 금액만큼 낮게 나온다. **거짓 선 발동 위험이 실제로 있다.**
  - 막는 방법은 두 갈래다: 미결제 매도 대금을 "자산에는 포함, 주문 가능 현금에는 미포함"으로 따로 확인해 쓰거나, 확인되지 않으면 선 판정을 보류(R0)한다. 2단계에서 정한다.

### 1i. HWM·선 발동·멈춤·R5 고점 저장 방법 (요구 4) — 두 안 비교

지금 있는 것:

| 자료 | 내용 | 쓰는 주체 | git |
|---|---|---|---|
| `stock-strategy-system/reconciliation_ledger.jsonl` | apply마다 한 줄, 해시 사슬, 보유·현금 `changes`와 확정 시각 | 사용자 확인 apply만 | 무시(`.gitignore:47`) |
| `stock-strategy-system/portfolio_state.json` | 최신 보유·현금 1벌(이력 없음) | apply만 | 무시(`:31`) |
| `stock-strategy-system/alert_runtime_state.json` | 평가기 이벤트 중복 억제 상태 | **예약 평가기**(`scripts/evaluate_alerts.py:1276-1331`) | 무시(`:32`) |
| `stock-strategy-system/decision_journal.json` | 없음. 다른 설계가 같은 경로를 예약(X7) | 미정 | **무시 목록에 없음** |
| 정규장 종가 이력 | 없음(1g) | — | — |

| | (A) 저장 없이 재계산 | (B) 새 상태 파일 + 확인 코드 쓰기 |
|---|---|---|
| 방식 | 대조 원장 + 종가 이력 + 입출금 신고로 매번 HWM·선·고점을 다시 계산. 사람 확인(검토 완료, 멈춤 해제)만 원장에 남김 | HWM·발동한 선·멈춤·종목 고점을 파일에 저장하고 갱신마다 확인 코드로 씀 |
| 새 쓰기 경로 | 사람 확인 기록 1종(추가만) | 상태 파일 쓰기 + 백업 + 원장(대조 apply와 같은 급) |
| 쓰는 빈도 | 선 발동·검토 때만 | 자산 신고점마다(HWM 갱신) 사용자 확인이 필요해짐 |
| 필요한 입력 | 적용일 이후 모든 세션의 종가, 모든 보유 변경이 원장에 있어야 함 | 최신 종가와 저장값 |
| 실패 모습 | 입력 구멍 → 계산 불가 → R0 | 파일 없음·손상 → R0 |
| 지난 값이 바뀌는가 | 늦은 대조가 들어오면 과거 구간 재계산 값이 달라질 수 있음 | 저장값은 그대로 |
| 결정론 | 같은 입력이면 같은 결과 | 쓰기 순서에 의존 |
| 예약 작업·Judge·Claude Code | 읽고 계산만 | 읽기만(쓰기는 Cowork 확인) |
| 코드 양 | 계산 모듈 + 추가 전용 원장 | 위 + 제안·확인·적용·백업 |

- 어느 쪽이든 종가 이력이 필요하다. (A)는 적용일부터 전 세션, (B)는 최신 세션. 1g의 30분봉 문제에 둘 다 걸린다.
- 원장은 I0 도입 뒤 apply만 담는다. 원장 첫 줄 날짜와 적용일 사이에 빈 구간이 있는지는 병합 뒤 Cowork가 확인해야 한다(확인 필요, 보유 값이라 읽지 않았다).
- 새 파일은 가격·보유 판단을 담으므로 `.gitignore`에 넣어야 한다.

### 1j. 표시 위치 — "E, 다음 선까지 거리, 멈춤 상태" 한 줄

| 파일 | 고정 | 넣을 곳 | 비고 |
|---|---|---|---|
| `scripts/build_holding_fact_pack.py` | — | `portfolio` 블록(`:445-458`)에 표시 블록 추가. 새 모듈 결과를 선택 입력으로 받음(`--alert-result`와 같은 방식, `:509`) | fact pack의 총액은 현재가(mark) 기준이라(`:345-350`) R4 자산과 다르다. 새 모듈 값을 그대로 옮기기만 한다 |
| `scripts/render_holding_cards.py` | — | 머리말(`:85-104`)에 한 줄 추가. 지금 `exposure` 칸은 카드 작성자가 쓰는 글이다(`:96`) | 문구는 `assets/locales/holding-card-ko-KR.json` |
| `scripts/validate_holding_card.py` | — | 변경 없음 | 표시 블록 키는 금지 규칙(`:30-36, 57-62`)을 피해야 한다(X9) |
| `scripts/portfolio_status.py` | — | 한 줄 요약(`:241-280`)에 항목 추가 | I7 현황 한 줄. `journal` 가정과 함께 손봐야 함(X7) |
| `scripts/portfolio_decision_dashboard.py` | — | 위험 지표 블록(`:1075-1133`) | 기존 한도표와 충돌(X8), worktree에서 검증 불가(X11). **이번에는 넣지 않는 쪽 제안** |

### 1k. 영향 테스트

서브에이전트가 읽기만으로 조사했다(테스트 실행 없음, 깨지는지는 단언문을 읽고 예측). 표의 줄 가운데 판단에 쓰는 것은 Builder가 다시 읽었다. "실제 정책"은 테스트가 디스크의 `alert_policy.json`·`instrument_registry.json`을 직접 읽는다는 뜻이다. 이런 테스트만 정책 수정에 반응한다.

요구 8의 12개:

| 테스트 | 실제 정책 | 영향받는 단언 | 원인 |
|---|---|---|---|
| `test_timing_engine.py` | 아니오(픽스처 `:48-111`) | 슬롯·anchor `:113, 203`, 재무장 `:133, 171, 210`, weakness_10ema 감시 `:267`, gap·halt `:289`, hard-risk 억제 `:336` | 엔진 수정 |
| `test_evaluate_timing_integration.py` | 예(`:61`), 실제 상태도 읽음(`:62`) | 슬롯 `:107`(B, MVLL-R25, 99주), anchor `:141`, NBIL `:155, 165`, D 등급 `:183, 198` | 정책 수정 |
| `test_portfolio_decision_dashboard.py` | 예(`:1559, 1599, 1620, 2567, 4096`) | 기준선 통과분 중 MVLL 축소 검토 `:2425, 2471`, 등록부 해시 일치 `:1598, 1661`. 나머지 관련 클래스는 기준선에서 이미 오류 | 정책 수정 |
| `test_reconcile_broker_state.py` | `:402`만 | `:401`(적용 후 검사) | 평가기 무결성 검사 수정 |
| `test_build_holding_fact_pack.py` | 아니오(`:115`) | 원가 한도 `:303-363`, 타이밍·방향 `:367-405` | fact pack 수정 |
| `test_holding_card.py` | 아니오 | `:302, 309` | fact pack 수정 |
| `test_v2_4_dual_phase.py` | 예(`:29-32`) | `:72`(NBIS 한도 값 필요) | 정책 수정 |
| `test_v2_5_leveraged_confirmation.py` | 예(`:17-18`) | `:50`(기존 규칙 불변) | 정책 수정(X16) |
| `test_v2_6_12_holding_valuation_shadow.py` | 예(`:384`) | `:389-401`(한도, 슬롯 수량, 재무장, `action_on_breach`) | 정책 수정(X16) |
| `test_v2_6_3_free_web_new_buy.py` | 예(`:33, 178, 180`) | `:222, 225, 228`. universe를 고치면 `:112`도 | 정책 수정(X16) |
| `test_v2_6_7_session_aware_kiwoom_priority.py` | 예(`:354, 357`) | `:505`(cohort 지문) | X15 |
| `test_v2_6_integration.py` | 예(`:55-68`) | `:63`(한도 + SOXL 슬롯 24), `:67`(등록부 `VALIDATED` + 설치 스킬 `PASS`) | 정책 수정, X10 |

그 밖:

| 테스트 | 영향받는 단언 | 원인 |
|---|---|---|
| `test_validate_research_packet.py` | `:56-68`(캐시의 SOXL·DRAM·NBIS·BE 승인 값이 false, 규칙의 수량 권한 어휘) | #12·#13 |
| `test_validate_decision_record.py` + 픽스처 | `:33`(NBIS에서 등록부·universe 불일치, `registry_version` 고정) | X3 |
| `test_v2_2_tactical_radar.py` | `:126, 133`(등록부 `VALIDATED`). universe를 고치면 `:74, 90, 197` | #12 동기화 |
| `test_v2_1_hardening.py` | universe의 SOXL 승인을 켤 때만 `:263` | X3 |
| `test_v2_4_automation.py` | `:54, 63`(`required` = `observed` = 원본) | 고정 파일 수정, X10 |
| `test_portfolio_decision_order_intent.py`, `test_k2_*` | `:1144`(해시 일치). 기준선에서 32개 오류 | #12 동기화 |

- 실제 등록부의 종목 집합이나 개수를 단언하는 테스트는 없다. 규칙 ID를 단언하는 테스트도 없다. 정책·등록부 해시 문자열을 박아 둔 테스트도 없다.
- `test_language_contract.py:20-22`는 `scripts/*.py` 전부가 ASCII인지 본다. 새 모듈과 평가기에 한글을 넣을 수 없다(문구는 locale 파일에 둔다).
- `test_evaluate_timing_integration.py`는 git이 무시하는 실제 `portfolio_state.json`을 읽는다. 상태가 바뀌면 결과가 달라지는 테스트다(기존 성질).

S7 Builder 정지 1단계

## 2. 계획과 결정 요청 (2단계, 코드·정책·상태 무변경)

- 입력: 1절, 지시문 5절(Cowork 1단계 검토, 30분봉 실측 K1~K6, 지침 5.2).
- 범위 밖 파일(X3·X6·X8·X14·X15)은 승인된 것으로 가정하지 않았다.
- 읽는 순서: 2.1(적용 방식과 빈틈) → 2.8(결정 요청). 나머지는 근거다.

### 2.0 추천 요약

| 항목 | 추천 |
|---|---|
| 적용 방식(P0) | **나눠서 적용.** 1차는 새 규칙을 더하기만 하고 옛 통제는 그대로 둔다. 2차에서 옛 통제를 은퇴한다 |
| 1차가 건드리는 고정 파일·범위 밖 파일 | 0개 |
| 1차의 빈틈(fail-open) | 없음(옛 알림이 계속 켜져 있다) |
| 1차의 "새 실패 0" | 지킬 수 있다(X10은 2차로 간다) |
| 가격 이력(P4) | 고정 파일 밖 증거 파일 방식 + 약 125세션으로 V 계산 |
| 저장 방법(P1) | 저장 없이 재계산, 사람 확인만 기록 |

### 2.1 적용 방식 두 안과 빈틈 (지침 5.2-3)

**(A) 한 번에 전체** — 5절 r2 전부(#1~#8, #12~#14), 고정 파일 2개, R6 대조 경로, 새 모듈을 한 커밋 묶음으로.

**(B) 나눠서**
- 1차(이 worktree): 새 계산·종가 증거·사람 확인 기록·표시를 **더한다.** 정책은 새 섹션 2개만 추가한다. 기존 키, 등록부, 고정 파일은 건드리지 않는다.
- 2차(새 worktree, 새 Judge): 옛 통제 은퇴(#1~#5, #8, #13, #14), 등록부(#12), 고정 파일 2개와 `deployment_gate`, R6 대조 신고, 범위 밖 파일 결정분. 시작 조건은 "새 통제가 실제 자료로 판정 가능함을 Cowork가 확인"이다.

옛 통제가 빠졌는데 새 통제가 판정하지 못하는 구간:

| 옛 통제 | 대신하는 새 통제 | 새 통제가 판정하려면 | (A)의 빈틈 | (B)의 빈틈 |
|---|---|---|---|---|
| 원가 한도 알림(D): SOXL −20%, MVLL −60%, NBIS −10% | R4 검토선 L1·L2…, R5 종목 고점 −30% | 정규장 종가(P4), 적용일·HWM 확인 기록(P1), 입출금 신고 경로(R6) | **있음.** 병합 순간 옛 알림이 꺼진다. Cowork가 종가 증거를 모으고(종목당 약 60쪽) 기록을 초기화하기 전까지, 그리고 매매·입출금 뒤 R6가 실제로 돌기 전까지 손실 검토 알림이 하나도 없다 | 없음(1차에는 옛 알림 유지, 2차는 새 선이 판정되는 것을 본 뒤) |
| SOXL·MVLL 축소 슬롯 검토(B) | R2 줄이기 권고(E ≥ 1.85, 종목 상한) | E = 종가 + V 이력 | **있음.** E가 "미확인"이면 낼 줄이기 권고 자체가 없다. r2의 "줄이기는 미확인 표시로 계속"은 비중을 알 때만 가능하다 | 없음 |
| 위반 시 신규 매수 멈춤(`freeze…`) | L2·R0 멈춤 | — | 없음. 수량 권한 none·현금 등 다른 hard gate가 매수 제안을 항상 `watch_only`로 묶는다(`scripts/validate_research_packet.py:515-516, 557-558`) | 없음 |
| SOXL weakness_10ema 감시, 재무장 | 없음(은퇴 승인됨) | — | 의도된 제거 | 2차에 제거 |
| gap·halt 감시 | 그대로 유지 | 엔진 수정이 정확해야 함 | 엔진 수정이 틀리면 감시가 사라진다. 테스트로 고정 | 2차에서 같은 위험 |
| NBIL de minimis | 없음 | — | 없음(보유 없음) | 없음 |

반대 방향(새로 열리는 것):

| 열리는 것 | (A) | (B) |
|---|---|---|
| 상품 승인 게이트(#12) | 병합과 함께 열림. 패킷 검증기에서는 계속 `watch_only`. universe까지 고치면 radar가 `ELIGIBLE_FOR_REVIEW`를 낼 수 있다(`scripts/run_tactical_opportunity_radar.py:139-149`, 수량 없음) | 2차까지 닫힌 채 |
| 채우기 권고 표시 | 병합과 함께 | 1차부터(표시 전용, B 이하). 지금 E가 1.85를 넘는 구간이라 당장은 나오지 않는다 |

(B)의 비용:
- 2차가 끝날 때까지 옛 알림(원가 한도 D, 슬롯 축소 검토)과 새 표시가 함께 나온다. 더 엄격한 쪽으로 겹칠 뿐 빠지는 통제는 없다.
- Judge가 두 번이다.
- 사용자 승인 5(상품 승인)·7(은퇴)의 실제 반영이 2차로 늦어진다.

**추천: (B).** 이유는 세 가지다. 빈틈이 생기지 않는 유일한 안이다. 1차는 고정 파일과 범위 밖 파일을 하나도 건드리지 않아 이 worktree에서 끝까지 검증된다. 종가 정의(K4)와 계좌 필드(X13)처럼 실측이 필요한 것을 옛 통제가 켜진 상태에서 확인할 수 있다.

### 2.2 파일별 변경

검토 순서 표기: NC = NO_CHANGE, RM = REMOVE/SIMPLIFY, RU = REUSE, RP = REPLACE, ADD.

**1차** (전부 비고정, 범위 밖 파일 없음)

| 순서 | 파일 | 종류 | K | 내용 |
|---|---|---|---|---|
| 1 | `scripts/portfolio_exposure.py` | ADD | K3 | 순수 함수(파일·시계·네트워크 없음): N·V·E, R0, R2, 줄이기 순서, R4, R5, R6 보류 판정, 실적 금지 구간, R9 표시 |
| 2 | `scripts/regular_session_close_history.py` | ADD | K3 | 키움 30분봉 쪽(page) 원문 → 정규장 종가 이력. 검증과 정규화만 한다(P4-b일 때) |
| 3 | `scripts/portfolio_review_journal.py` | ADD | K3 | 사람 확인 기록: 읽기·사슬 검증, 확인 코드로 한 줄 추가(새 쓰기 경로) |
| 4 | `scripts/run_portfolio_exposure_review.py` | ADD | K2 | 입력을 읽어 1을 부르고 결과 파일을 쓴다. 상태·정책·원장·기록은 읽기만 |
| 5 | `schemas/portfolio-exposure-review.schema.json`, `regular-session-close-history.schema.json`, `portfolio-review-journal.schema.json` | ADD | K2 | 출력·증거·기록 형식 |
| 6 | `assets/locales/portfolio-exposure-ko-KR.json` | ADD | K1 | 한글 문구(스크립트는 ASCII 유지) |
| 7 | `stock-strategy-system/alert_policy.json` | 수정 | K3 | 최상위 새 섹션 2개 **추가만.** 기존 키 무변경 |
| 8 | `scripts/build_holding_fact_pack.py` | 수정 | K2 | 선택 입력 `--exposure-review`. 있으면 `portfolio` 블록에 그대로 옮긴다. 없으면 출력 불변 |
| 9 | `scripts/render_holding_cards.py`, `assets/locales/holding-card-ko-KR.json` | 수정 | K1 | 머리말 한 줄(블록이 있을 때만) |
| 10 | `scripts/portfolio_status.py`, `assets/locales/portfolio-status-ko-KR.json` | 수정 | K1 | 한 줄 항목, 기록 형식 가정 수정(X7) |
| 11 | `.gitignore` | 수정 | K1 | 기록 파일, 종가 증거 폴더, 결과 폴더 |
| 12 | 새 테스트 4개 + `test_build_holding_fact_pack`·`test_holding_card`·`test_portfolio_status` 보강 | ADD | K2 | 지시문 "테스트 사례" 전부, 필수 수정 5~11마다 fail-closed 테스트 |
| 13 | `references/portfolio-exposure-review.md` | ADD | K0 | 절차 문서(수집, 초기화, 검토 완료 기록) |

- 되돌리기: 커밋 되돌림. 전부 추가라 옛 동작은 바뀌지 않는다. 기록·증거 파일은 git 무시 대상이라 남아도 영향이 없다.
- 정책 영향(1d): `rules_hash`가 바뀌어 평가기 이벤트 중복 억제가 한 번 초기화된다. shadow cohort 지문은 바뀌지 않는다(해시 재료가 아님). 예약 런타임 배포 때 manifest 재생성이 필요하다.

**2차** ((A)를 고르면 1차와 한 묶음)

| 순서 | 파일 | 고정 | K | 내용 |
|---|---|---|---|---|
| 1 | `workspace/policies/instrument_registry.json` | — | K3 | #12. MU·DELL·AMD·TQQQ 추가(1차 출처), 8개 승인, `registry_version` |
| 2 | `stock-strategy-system/alert_policy.json` | — | K3 | #12 해시·캐시, #13, #1~#8, #14, `deployment_gate` 해시, 새 섹션 `status` |
| 3 | `scripts/timing_engine.py` | **G** | K3 | 은퇴 종목: anchor 검사 건너뜀, 슬롯 없이 gap·halt만(X1, X12) |
| 4 | `scripts/evaluate_alerts.py` | **G** | K3 | 원가 한도 판정 제거, 등록부 검사 변경(X2), 타이밍 호출부 |
| 5 | `scripts/validate_research_packet.py` | — | K2 | 원가 한도 은퇴 반영, 보유 레버리지 상품 검사를 새 등록부로 |
| 6 | `scripts/build_holding_fact_pack.py` | — | K2 | 원가 한도 칸을 "은퇴"로, 규칙 방향에 S5 근거 추가 |
| 7 | `scripts/reconcile_broker_state.py`, `kiwoom_broker_shadow.py`, `apply_user_confirmed_broker_snapshot.py`, 대조안 스키마, 대조 locale | — | K3 | R6 신고(P8-6) |
| 8 | 기존 테스트(1k), 결정 기록 픽스처 | — | K2 | X16 포함 |
| 9 | `workspace/state/integrated_shadow/shadow_progress.json` + 보관 1개 | — | K2 | X15(결정 시) |
| 10 | `workspace/policies/tactical_candidate_universe.json` | — | K3 | X3(결정 시) |
| 11 | `references/*.md`, `stock-strategy-system/*PROMPT*.md` | — | K0 | 원가 한도·슬롯 설명 정리(`references/yfinance-data.md`는 고정이라 제외) |

- 되돌리기: 커밋 되돌림 + 설치 스킬 되돌림 + 런타임 manifest 재생성. cohort 이관은 한 방향이다(되돌리면 새 cohort가 다시 시작된다). 엔진·평가기는 정책 표시(은퇴 여부)를 보고 갈라지게 짜서, 정책만 되돌려도 옛 동작으로 돌아간다.

고치지 않는 것(두 안 공통): acceptance 16개, `scripts/build_market_snapshot.py`, `references/yfinance-data.md`, `SKILL.md`, `assets/locales/ko-KR.json`, `scripts/portfolio_decision_dashboard.py`, `portfolio_state.json`, 대조 원장, `backups/`.

### 2.3 R0~R9 → 함수·파일 대응

| 규칙 | 함수(`scripts/portfolio_exposure.py`) | 재사용·신규 |
|---|---|---|
| R0 | `fail_closed_status` — 트리거 7개를 코드로 모아 `pause`(채우기·신규 매수)와 "미확인" 표시를 낸다. 각 계산 함수는 값 대신 사유 코드를 돌려준다 | ADD. 대조 나이 판정 식은 평가기와 같은 식(`scripts/evaluate_alerts.py:460-470`)을 쓴다. 평가기는 고정이라 import하지 않고 정책 값 `broker_snapshot_max_age_calendar_days`만 공유한다 |
| R1 N | `nominal_exposure` — 정책 `nominal_multipliers`, 미등록 보유면 계산 불가 | ADD. 현황판에 같은 산술이 있지만(`scripts/portfolio_decision_dashboard.py:1086`) 그 모듈은 import하지 않는다(X11). 등록부에 있는 종목은 `leverage_factor`와 같은지 대조한다(RU) |
| R1 V | `sox_equivalent_ratio` — 현재 비중 고정, 공통 세션 창, 252·최소 60 | ADD |
| R1 종가 | `regular_session_close_history.select_close` — 세션 달력의 `core_close_at`으로 봉 선택 | ADD. 달력은 `scripts/session_authority.py` 결과를 입력으로 받는다(RU) |
| R1 E | `effective_exposure = max(N, V)` | ADD |
| R2 | `band_action`(≥ 1.9, ≥ 1.85, ≤ 1.25, 그 사이), `projected_exposure`, `filter_exposure_increasing`(채우기·대역 안 신규 매수·교체 매수 쪽), `add_target`, `reduce_order` | ADD |
| R3 | `single_stock_cap_status`(0.4, 대상·면제 목록), `earnings_blackout`(미확인 = 금지, MU → DRAM 대체 금지) | ADD. 금지 구간 문장은 기존 키를 참조만 한다 |
| R4 | `equity_series`, `hwm_and_lines`(반올림 전 `≤`, 선마다 1회, 새 HWM 재무장, "계속" 뒤 다음 선) | ADD |
| R5 | `peak_review`(적용일·첫 대조 확인일 이후 고점, `≤ 고점 × 0.70`, 기준 고점 없으면 채우기 멈춤) | ADD. 비활성 `peak_drawdown` 초안은 건드리지 않는다(NC) |
| R6 | `cash_flow_status`(미신고면 HWM·선 보류 + 멈춤) + 2차의 대조 신고 | ADD / 대조는 수정 |
| R7 | 2차: 정책 표시 + 엔진·평가기 분기 | RM |
| R8 | 정책에 설정만 기록, 원장은 별도 K2(P7) | — |
| R9 | `swap_legs` — 매도 쪽 먼저, 매수 쪽은 확인된 주문 가능 현금이 있을 때만 표시 | ADD |

출력은 목표 비중뿐이다. 모든 결과에 `order_authority=false`, `quantity_authority="none"`, `execution_quantity=null`을 넣고 스키마로 고정한다.

### 2.4 계획 본문에서 처리하는 X 항목 (지침 5.2-4)

| # | 처리 방법 | 단계 |
|---|---|---|
| X1 | 슬롯 배열과 `anchor_shares`는 지우지 않고 종목 항목에 은퇴 표시 키를 둔다. 엔진은 표시가 있으면 anchor·슬롯 검사를 건너뛰고 상태의 `timing_plan`을 읽지 않는다. 상태 쓰기는 없다. `holding_timing_rules.policy_version`은 그대로 둔다 | 2차 |
| X2 | 보유 등록부를 `portfolio_exposure_policy.nominal_multipliers`의 종목 집합으로 옮긴다. 평가기는 "보유 ⊆ 등록 상품"만 검사하고 "정책 종목은 모두 보유" 검사는 원가 한도 은퇴와 함께 끈다. 미등록 보유는 지금처럼 F다 | 2차 |
| X7 | r2 경로(`decision_journal.json`)를 그대로 쓰되 줄마다 `entry_type`을 둔다. `portfolio_status.py`는 카드 결정 종류만 "채점 대기"로 센다. 쓰기는 새 CLI의 확인 코드 경로 하나뿐이다. `tactical_radar_policy.json`의 "decision_journal" 문구는 코드가 없는 선언이라 건드리지 않고, 병합 뒤 규칙 정리 목록에 올린다 | 1차 |
| X9 | 권고(목표 비중)는 카드 JSON에 넣지 않는다. 노출 점검 결과 파일에만 둔다. 카드·fact pack에는 "E, 다음 선까지 거리, 멈춤 상태"만 옮기고 키 이름은 카드 금지 규칙을 피한다 | 1차 |
| X12 | 은퇴 종목의 gap 감시는 원가 한도 경계 항을 빼고 계산한다(기술 항 2개: 전 10일 저가 − 0.25 ATR, EMA20 − 0.75 ATR). `definitions`의 문장은 다른 정책이 참조하므로 남긴다. 문장과 동작이 한 항 다르다는 점을 문서에 적고 Judge가 본다 | 2차 |
| X13 | 계좌 응답 실측이 먼저다(2.9). 그 전에는 설계를 확정하지 않는다. 실측 전 기본 규칙: 대조에서 보유가 줄어든 직후에는 그 다음 날짜의 대조가 현금을 확인할 때까지 선 판정을 보류한다(거짓 선 발동 방지) | P8-6 |
| X16 | 원가 한도 값과 슬롯 수량은 정책에 그대로 남으므로 "값 불변" 단언은 계속 통과한다. 테스트 이름·주석이 "규칙이 살아 있다"로 읽히는 곳은 "값은 보존, 판정은 은퇴"로 고치고 은퇴 표시 단언을 더한다. 바꾼 목록은 Judge에게 표로 준다 | 2차 |

### 2.5 범위 밖 파일이 필요한 항목 (지침 5.2-2)

| # | 파일 | 이번에 포함 | 별도 단계로 미룸 | 하지 않음 | 미루면 S7에서 빠지는 것 | 추천 |
|---|---|---|---|---|---|---|
| X3 | `tactical_candidate_universe.json` | SOXL·NBIS·BE의 `new_buy_approved`를 켜고 lane 값 정리 | #12 승인 켜기와 함께 2차 | 등록부만 켜고 불일치 오류 감수 | 상품 승인 게이트 개방. 매수 제안은 어차피 `watch_only`라 표시는 같다 | 2차로 미룸 |
| X6 | `kiwoom_runtime_bridge.py`(고정), `kiwoom-readonly-policy.json` | P4-a | — | P4-b 또는 c | P4 참고 | P4-b |
| X8 | `portfolio-decision-risk-envelope-v0.2.json`, 현황판 | 한도표에 "S5로 대체" 표시 + 현황판 수정 | 원본 폴더에서 별도 작업 | 두 표시 공존 | 현황판이 옛 기준(상한 125%, 현금 하한 10%)으로 `VIOLATION`을 계속 낸다. 카드·상태 한 줄의 S5 표시와 엇갈린다 | 미룸(이 worktree에서 현황판 검증 불가) |
| X14 | `integrated_identity_session_activation.json`, `kiwoom-session-aware-priority-policy.json` | 불가(Production 권한 원본, acceptance 고정) | 별도 K3 | — | MU·DELL·AMD·TQQQ를 실제로 사면 수동 분석이 미확인 종목으로 처리하고 평가기가 F가 된다. "카드 종목 코어로 채우기"는 표시만 되고, 사기 전에 이 K3가 끝나야 한다 | 별도 K3로 미룸 |
| X15 | `shadow_progress.json` | 이관 스크립트 실행(상태 1개 갱신 + 보관 1개, 카운터 0이라 손실 없음) | 2차 | 테스트 1건 실패 감수 | 없음(1차는 지문이 안 바뀐다) | 2차에 포함 |
| X5 | 정책 캐시의 BE·DRAM 신원 필드 | BE(SEC 10-K)·DRAM(운용사 투자설명서) 1차 출처 확인 추가 | X14와 함께 | — | BE·DRAM을 사면 평가기가 F | X14와 함께 미룸 |

### 2.6 설치 스킬 동기화 전 실패가 예상되는 테스트 (지침 5.2-5)

- (B) 1차: **없음.** 고정 파일을 고치지 않는다.
- 2차 또는 (A): 아래는 "새 실패 0" 판정에서 따로 센다. Judge가 원인이 이것뿐인지 확인한다.

| 테스트 ID | 이유 | 풀리는 때 |
|---|---|---|
| `test_int_14_deployment_and_registry_hashes_match (test_v2_6_integration.V26IntegrationTests.test_int_14_deployment_and_registry_hashes_match)` | 설치 폴더(`~/.codex/skills/…`)의 `timing_engine.py`·`evaluate_alerts.py`가 옛 해시다(`tests/test_v2_6_integration.py:68`) | 사용자가 설치 스킬을 동기화한 뒤 |
| `test_deployment_gate_hashes_match_canonical_source (test_v2_4_automation.V24AutomationTests.…)` | P5에서 ②(observed를 옛 값으로 둠)를 고를 때만 실패(`tests/test_v2_4_automation.py:61`) | 동기화 뒤 observed를 갱신하면 |
| `test_deployment_validator_detects_mismatch (test_v2_4_automation.V24AutomationTests.…)` | 위와 같음(`:66`) | 위와 같음 |

### 2.7 계획 기본값 (따로 묻지 않는다. 다르게 하려면 번호로 알려 달라)

| # | 기본값 | 근거 |
|---|---|---|
| D1 | 줄이기·채우기의 목표 비중은 "예상 E가 1.55가 되는 비중"이다. 늘리는 쪽은 ≤ 1.55, 줄이는 쪽은 1.55까지 | r2에 글자로는 없다. 부록 C.6의 "1.55를 맞추려면 SOXL 약 28%"를 따랐다. **해석이 들어간 값** |
| D2 | 줄이기 순서 ①은 상한(명목 0.4)까지, ②카드 TRIM은 종목만 표시(비중은 카드 판단, EXIT는 0), ③SOXL은 ①을 반영한 뒤 1.55까지 | 카드에 목표 비중을 둘 수 없다(X9) |
| D3 | 보유 종목의 이력이 60세션 미만이면 V 계산 불가(R0) | r2는 신규 편입만 적었다. fail-closed로 채움 |
| D4 | 카드 ADD·TRIM은 "검증기 통과 + 그 카드의 기준 세션이 이번 판정 세션과 같음"일 때만 쓴다 | 요구 7의 "유효 기간"을 가장 좁게 읽음 |
| D5 | 적용일 이후 종가가 하루라도 비면 HWM·선은 "미확인"(R0). 비는 날을 건너뛰어 계산하지 않는다 | 건너뛰면 HWM이 낮게 잡혀 선이 느슨해진다 |
| D6 | 원가 한도 값·슬롯 배열은 정책에 남기고 은퇴 표시 키로 끈다(2차) | 값을 지우면 현황판 `:517-518`이 깨지는데 그 테스트를 여기서 돌릴 수 없다. 되돌리기도 쉽다 |
| D7 | 엔진·평가기는 정책 표시로 갈라진다. 옛 경로 코드는 남긴다 | 되돌리기와 기존 픽스처 테스트 유지. 정리는 나중 K2 |
| D8 | 새 섹션 `policy_version`은 `2026-10-01-s5-r2`. `strategy_version`과 `holding_timing_rules.policy_version`은 바꾸지 않는다 | 상태와 묶인 값이라 올리면 평가기가 F(1d) |
| D9 | 1차에서 아직 사실이 아닌 r2 문구(상품 승인 게이트 "opened…")는 "2차 대기" 값으로 둔다 | 정책에 거짓 진술을 두지 않는다 |
| D10 | 저가·고가는 쓰지 않는다. 고른 봉의 값 하나만 쓴다 | K5(저가 이상치) |
| D11 | 표준편차는 양쪽 같은 식(표본)으로 계산한다 | 비율이라 식 선택은 결과에 영향이 없다 |
| D12 | 결과 파일은 `workspace/outputs/exposure-review/<세션>/`, 종가 증거는 `workspace/outputs/regular-session-closes/`. 둘 다 git 무시 | 보유·평가액이 들어간다 |

### 2.8 결정 요청

한 번에 하나씩 답하면 된다. **P0~P4, P6, P7은 지금 필요하다.** P5와 P8은 (B)를 고르면 2차 지시문에서 다시 묻는다(지금은 추천만 본다). (A)를 고르면 전부 지금 필요하다.

**P0. 한 번에 적용할까, 나눠서 적용할까?**
- ① 나눠서: 1차는 더하기만, 옛 알림 유지. 2차에서 은퇴. **(추천)**
- ② 한 번에: 병합 순간 옛 알림이 꺼진다.
- 추천 이유: ②는 새 선이 실제로 돌기 전까지 손실 검토 알림이 없는 구간이 생긴다(2.1).

**P1. HWM·선·멈춤·종목 고점을 어떻게 보관할까?**
- ① 저장하지 않고 매번 다시 계산한다. 사람이 확인한 것(적용 시작, 검토 완료, 멈춤 해제)만 기록한다. **(추천)**
- ② 새 상태 파일에 저장하고 바뀔 때마다 확인 코드로 쓴다.
- 추천 이유: ②는 자산이 신고점을 찍을 때마다 사용자 확인이 필요해진다. ①은 쓰는 일이 선 발동·검토 때뿐이다.
- 함께 정해지는 것: 기록 파일은 r2대로 `stock-strategy-system/decision_journal.json`(git 무시 추가), 쓰기는 Cowork에서 사용자가 `확인 <코드>`를 보낸 뒤에만.

**P2. 알림 등급을 어떻게 매길까?**
- ① L1 = C, L2와 이후 선 = D, E ≥ 1.85 = B, E ≥ 1.9 = D, R5(종목 고점 −30%) = B, R0(미확인) = B에 "미확인" 표시, 채우기 = B. **(추천)**
- ② D를 쓰지 않는다: L1 = C, 나머지 전부 B.
- 추천 이유: D는 지금 "손실 경계 검토"에만 쓰는 등급이고 원가 한도가 은퇴하면 비게 된다. 포트폴리오 −20% 선과 절대 상한이 그 자리를 잇는 것이 자연스럽다. R0를 F로 하지 않는 이유는 F가 "모든 후보 중지"라서 줄이기 권고까지 막기 때문이다.
- ①을 고르면 `alert_grades.D` 설명 문장에 "포트폴리오 검토선·절대 상한"을 더한다. 이것은 5절 r2에 없는 경로라 이 답이 곧 그 승인이다(2차에 반영).

**P3. "정규장 종가"를 30분봉의 어느 값으로 볼까?** (K3·K4: 봉은 시작 시각 표기, 16:00 봉 종가에는 16:00~16:30 시간외 체결이 들어간다)
- ① 16:00 봉의 **시가**(마감 동시호가로 추정). **(조건부 추천)**
- ② 15:30 봉의 종가(정규장 마지막 30분, 동시호가 제외).
- ③ 16:00 봉의 종가(r2 글자 그대로, 시간외 30분 포함).
- 추천 이유: SOXX 9/30에서 ③은 ①보다 0.38% 높았다. 기존 허용 오차(0.1%)를 매일 넘길 수 있다. 다만 ①이 공식 종가와 맞는지는 아직 가설이다.
- 조건: Cowork가 10세션 × 3종목 이상에서 ①·②·③을 공식 종가와 대조한 표를 먼저 낸다(2.9). 표가 다르게 나오면 이 질문을 다시 한다.
- 함께 정해지는 것
  - 조기 폐장일은 같은 규칙을 폐장 시각 기준으로 적용한다.
  - 허용 오차는 기존 식 `max($0.05, 종가 × 0.001)`을 다시 쓴다(`alert_policy.json:114`).
  - 참고 종가(Yahoo)가 입력에 있으면 대조하고, 넘으면 그 종목은 "미확인"(R0)이다. 참고 종가가 없으면 "대조 안 함"으로 표시만 한다. 평균은 내지 않는다.
  - HWM 시작값 $28,473.94는 ③으로 계산한 값이다. ①·②를 고르면 적용일 재확인 때 같은 정의로 다시 계산하고, 차이를 사용자 확인 기록에 남긴다.

**P4-1. 30분봉 가격 이력을 어디서 가져올까?**
- ⓐ 고정 브리지와 `kiwoom-readonly-policy.json`을 확장한다(별도 K3).
- ⓑ 고정 파일 밖에서 수집하고 증거 파일로 넣는다: Cowork·사용자가 키움 공식 CLI(조회 전용)로 받은 쪽을 저장하고, repo의 새 스크립트는 검증·정규화만 한다. **(추천)**
- ⓒ 가져오지 않는다. V·E·R4·R5는 "미확인"으로 둔다.

| | 멈추는 것 | 비용 |
|---|---|---|
| ⓐ | K3가 끝날 때까지 ⓒ와 같다 | acceptance 불일치 파일이 2개에서 3개로 늘고 shadow cohort가 다시 바뀐다. 시세 승인 범위(X14)에 없는 종목은 여전히 못 읽는다 |
| ⓑ | 수집을 거른 날은 그날 판정이 "미확인"(나중에 채울 수 있다) | 매일 종목당 1쪽 수집(처음 한 번은 종목당 약 60쪽). 사람 손을 거친 증거라 쪽 해시·연속성·달력 대조로 검증한다 |
| ⓒ | 채우기·신규 매수 권고 멈춤, 줄이기·검토선·종목 고점 판정 불가. 표시는 "미확인" 한 줄뿐 | 없음. 단 옛 통제를 은퇴하면 안 된다(빈틈) |

- 추천 이유: ⓑ만 승인 범위 안에서 지금 검증할 수 있다. ⓐ는 나중에 자동화할 때 별도로 하면 된다.

**P4-2. 이력이 약 125세션뿐이다(2026-04-01부터). 그 길이로 V를 계산할까?**
- ① 예. r2의 "252 미만이면 가용 세션(최소 60)"을 보관 한계에도 적용하고 "짧은 이력"으로 표시한다. 모은 쪽을 계속 쌓아 252까지 늘린다. **(추천)**
- ② 아니오. 252세션이 찰 때까지 V는 "미확인"이다.
- 추천 이유: ②는 2027년 봄까지 E 전체가 "미확인"이라 P4-1의 ⓒ와 같아진다.
- 확인 필요(Cowork): 6개월 이동 보관인지 고정 시작일인지(K1), `upd_stkpc_tp` "1f"의 의미(K6), 서머타임 표기(K3).

**P5. (2차) 고정 파일 해시를 어떻게 갱신할까?**
- ① `required`와 `observed`를 모두 새 원본 해시로 바꾼다. 병합 뒤 사용자가 설치 스킬을 동기화하면 그대로 통과한다. 그 사이 실패 테스트 1건(2.6). **(추천)**
- ② `required`만 새 값으로, `observed`는 옛 값으로 둔다. 동기화 뒤 정책을 한 번 더 고친다. 그 사이 실패 테스트 3건.
- 추천 이유: ②가 더 정직하지만 승인 정책을 두 번 고쳐야 한다. ①에서도 실제 설치 폴더가 다르면 검증기가 `MISMATCH`를 내므로 예약 실행은 막힌다(`scripts/validate_skill_deployment.py:43-45`).
- 어느 쪽이든 `status`는 지금 글자를 유지해야 한다(다르면 검증 실패, `:56-57`). `verified_at_kst`는 동기화 확인 때 Cowork가 사용자 승인으로 고친다.

**P6. "S7 적용일"을 무엇으로 정할까?**
- ① Cowork에서 사용자가 확인한 "적용 시작" 기록의 날짜. 그 기록에 재확인한 HWM을 함께 남긴다. **(추천)**
- ② 병합 커밋 날짜.
- ③ 정책 파일에 날짜를 적는다.
- 추천 이유: 기록이 없으면 r2대로 R0라서, 준비(종가 증거, HWM 재확인)가 끝나기 전에 선이 도는 일이 없다. ③은 날짜 때문에 승인 정책을 다시 고쳐야 한다.
- 함께 정해지는 것(1차 기준): 새 섹션 `status`는 `approved_display_only_old_controls_retained`, 2차에서 `approved_display_only`로 바꾼다.
- 병합 뒤 작업(Builder는 하지 않는다)
  1. 사용자: 원본 폴더 병합.
  2. Cowork: 종가 증거 수집(SOXX + 보유 종목, 2026-04-01부터)과 검증.
  3. Cowork: 9/30~적용일 종가 자산 고점으로 HWM 재확인 → 사용자 `확인 <코드>` → "적용 시작" 기록.
  4. Cowork: 보유 종목 기준 카드 1회(R5).
  5. 사용자: Claude Code·예약 작업·Judge가 기록 쓰기 명령을 못 쓰게 규칙 추가(`CLAUDE.md`, 권한 설정).
  6. 이후 매 세션: 종가 수집 1쪽씩 → 노출 점검 실행(당분간 수동, 예약 연결은 별도).
  7. 예약 런타임 배포는 급하지 않다(1차는 예약 평가기를 바꾸지 않는다). 배포할 때 manifest 재생성.
  8. (2차 뒤) 설치 스킬 동기화, cohort 확인.

**P7. K132-G 보고 전용 가상 운용 원장을 이번에 만들까?**
- ① 별도 K2로 뺀다. 정책에는 설정만 적는다. **(추천)**
- ② 이번에 만든다.
- 추천 이유: 정책 효과가 없는 Cold Path다. K3 Judge 범위를 넓힐 이유가 없다.

**P8. 범위 밖 파일과 그 밖의 미결정** ((B)면 2차 지시문에서 다시 묻는다)

| # | 질문 | 선택지 | 추천 |
|---|---|---|---|
| P8-1 (X3) | tactical universe도 고칠까? | 포함 / 2차에 #12와 함께 / 하지 않음 | 2차에 #12와 함께 |
| P8-2 (X8) | 현황판 위험 한도표를 S5에 맞출까? | 포함 / 원본 폴더에서 별도 작업 / 그대로 둠 | 별도 작업 |
| P8-3 (X14) | MU·DELL·AMD·TQQQ의 신원·시세 범위 등록은? | 별도 K3 / 하지 않음 | 별도 K3. 사기 전에 끝낸다 |
| P8-4 (X15) | shadow cohort 상태 파일을 이관할까? | 2차에 포함 / 테스트 1건 실패 감수 | 2차에 포함 |
| P8-5 (X5) | BE·DRAM 신원 출처도 확인할까? | P8-3과 함께 / 하지 않음 | P8-3과 함께 |
| P8-6 (X13) | R6 입출금 신고(대조 쓰기 경로 수정)는 언제? | 계좌 응답 실측 뒤 1차에 포함 / 2차 | 실측 뒤 1차에 포함. 2차로 미루면 그동안 매매·입출금이 있은 뒤의 검토선은 "보류"로만 나온다 |

### 2.9 구현 전에 Cowork에서 받아야 할 것 (읽기 전용 실측, Builder는 키움 도구를 쓰지 않는다)

| # | 받을 것 | 쓰는 곳 |
|---|---|---|
| C11 | 30분봉 쪽 원문 표본: 평일 1일(15:30·16:00 봉 포함), 2026-04-01 이후 조기 폐장일 1일(날짜는 세션 달력으로 확인), 쪽 경계가 보이는 연속 2쪽. 가격 자료라 픽스처로 쓸 수 있다 | `regular_session_close_history.py` 형식과 테스트 |
| C12 | P3 대조표: 10세션 × 3종목 이상에서 16:00 봉 시가·15:30 봉 종가·16:00 봉 종가와 공식 종가 | P3 확정 |
| C13 | K1·K3·K6 확인(보관 방식, 서머타임, "1f") | P4-2, 수정주가 처리 |
| C14 | 계좌 응답 의미: 체결 조회가 며칠 치를 주는지, 매도 직후 `fc_ord_alowa`·`fc_pymn_alowa`·`fc_entra`와 `d1/d2` 필드가 어떻게 바뀌는지. 금액은 가려도 된다 | R6 설계(P8-6), 미결제 매도 대금 |
| C15 | 대조 원장 첫 줄 날짜와 그 뒤 상태 revision이 끊김 없이 이어지는지 | P1 ①의 재계산 입력 |

S7 Builder 정지 2단계

## 3. 구현 (1차, 지시문 6·7·8절)

- 승인 근거: 사용자 결정 P0(나눠서)·P1·P2·P3·P4-1·P4-2·P6·P7·P8-6(지시문 6절), Cowork 실측 C11~C15(7절), 3단계 지침(8절). 기본값 D1~D12 적용.
- 범위: 1차만. 기존 정책 키, 등록부, 고정 파일(`deployment_gate` 6, acceptance 16), 범위 밖 파일은 건드리지 않았다. 커밋하지 않았다.
- 권한: 새 출력·새 규칙 모두 `order_authority=false`, `quantity_authority="none"`, `execution_quantity=null`. 출력은 목표 비중뿐이다. 키움 실행 도구는 쓰지 않았다(명세 문서 파일 `kiwoom_api_spec.json`의 `ust21100` 항목만 읽음). 상태·원장·`backups/`·실제 `decision_journal.json`은 만들거나 쓰지 않았다.

### 3.1 지시문 3단계 하위 항목별 결과

| 항목 | 1차 결과 |
|---|---|
| 3a 상품 등록(#12) | 2차. 등록부·캐시·`required_canonical_sha256` 무변경. `validate_registry_consistency.py` `VALIDATED`(4.4) |
| 3b `approved_rule_registry`(#13) | 2차. 7개 항목 무변경 |
| 3c 정책 | 새 섹션 2개 **추가만**(`portfolio_exposure_policy`, `portfolio_review_lines`). #1~#8·#14는 2차 |
| 3d 계산 모듈 | `scripts/portfolio_exposure.py`(순수 함수). N·V·E, R0, 대역, 종목 상한, 줄이기 순서, 채우기·신규 매수·교체 매수 쪽의 예상 E와 상한, R4 선, R5, R6 보류, 실적 금지 구간, MU → DRAM 대체 금지, R9 |
| 3e 평가기·타이밍 엔진 | 2차. `timing_engine.py`·`evaluate_alerts.py` 무변경(해시 동일, 4.5) |
| 3f 대조 R6 신고 | 1차에 포함(P8-6). `reconcile_broker_state.py propose`에 선택 입력 2개, 대조안에 `cash_flow_declaration` 블록, apply가 원장에 기록 |
| 3g 표시 한 줄 | fact pack(선택 입력) → 카드 머리말 한 줄, 상태 한 줄(`portfolio_status.py`), 실행기 요약 |
| 3h K132-G | 하지 않음(P7). 정책에 설정만 |

### 3.2 바뀐 파일

경로는 `manage-us-stock-strategy/` 아래(정책·`.gitignore` 제외). 고정 = `deployment_gate` 6 또는 acceptance 16.

새 파일(24개 + 픽스처 2개, 3.7 반영 뒤)

| 파일 | K | 줄 | 내용 |
|---|---|---|---|
| `scripts/portfolio_exposure.py` | K3 | 1,333 | 순수 계산(파일·시계·네트워크 없음). 표시 블록·한 줄 문장 조립 포함 |
| `scripts/regular_session_close_history.py` | K3 | 338 | 저장된 키움 30분봉 쪽 검증 → 정규장 종가 이력. 키움 호출 없음 |
| `scripts/cash_flow_evidence.py` | K3 | 439 | 저장된 `ust21100` 거래내역 정리(계좌 표시 제거)·분류, 신고 블록, 신고 사슬 판정 |
| `scripts/portfolio_review_journal.py` | K3 | 395 | 사람 확인 기록. 쓰기는 `apply`(확인 코드) 하나뿐 |
| `scripts/run_portfolio_exposure_review.py` | K2 | 438 | 입력 읽기 → 계산 → 결과 파일. 상태·정책·원장·기록은 읽기만(실행 전후 해시 대조) |
| `schemas/portfolio-exposure-review.schema.json` | K2 | 286 | 결과 형식. 권한 3필드 const |
| `schemas/regular-session-close-history.schema.json` | K2 | 108 | 종가 이력 형식 |
| `schemas/portfolio-review-journal.schema.json`, `…-payload…`, `…-proposal…` | K2 | 98 | 기록·제안 형식 |
| `schemas/kiwoom-cash-flow-evidence.schema.json`, `cash-flow-declaration.schema.json` | K2 | 141 | 거래내역 증거, 신고 블록 |
| `assets/locales/portfolio-exposure-ko-KR.json` | K1 | 41 | 한글 문구(스크립트는 ASCII 유지) |
| `assets/kiwoom-transaction-history-classification.json` | K2 | 44 | 거래내역 분류 낱말표(배당·수수료/세금/이자·환전·매매·입금·출금) |
| `references/portfolio-exposure-review.md` | K0 | 200 | 절차 문서 |
| `tests/test_portfolio_exposure.py` 등 8개 + `tests/s5_exposure_fixtures.py` | K2 | 3,066 | 새 테스트 170개(Judge 재현 `test_portfolio_exposure_judge_fixes.py` 29개 포함) |
| `tests/fixtures/regular-session-closes/SOXX/soxx_30m_20260930_p1.json`, `…_p2.json` | — | — | Cowork 표본 복사(시세 자료만, sha256 `d93580b0…`, `a115684d…`). 표본 README는 "커밋 전 별도 승인"이라 적었다. 지침 8-4에 따라 픽스처로 썼다 |

고친 파일(12개, 전부 비고정)

| 파일 | K | 변경 | 내용 |
|---|---|---|---|
| `stock-strategy-system/alert_policy.json` | K3 | +161 | 새 섹션 2개. 기존 키 무변경(4.6) |
| `scripts/kiwoom_broker_shadow.py` | K3 | +9 −1 | `reconciliation_proposal(..., cash_flow_declaration=None)`. 없으면 출력이 이전과 같다 |
| `scripts/apply_user_confirmed_broker_snapshot.py` | K3 | +9 | 블록 자기 일관성 재검사, 원장 줄에 블록 기록(있을 때만). 상태 필드는 늘지 않는다 |
| `scripts/reconcile_broker_state.py` | K3 | +39 | `propose --cash-flow-evidence --declare-cash-flow-usd`, `show`에 신고 줄 |
| `schemas/kiwoom-reconciliation-proposal.schema.json` | K3 | +1 | 선택 속성 `cash_flow_declaration`(스키마 버전 문자열은 그대로) |
| `assets/locales/reconcile-broker-state-ko-KR.json` | K1 | +7 | 신고 문구 |
| `scripts/build_holding_fact_pack.py` | K2 | +27 | 선택 입력 `--exposure-review`. 없으면 fact pack이 이전과 같다 |
| `scripts/render_holding_cards.py` | K1 | +19 | 머리말에 S5 한 줄(블록이 있을 때만) |
| `scripts/portfolio_status.py` | K1 | +39 −1 | 최신 노출 점검 한 줄, S5 확인 기록은 "채점 대기"에서 제외(X7) |
| `references/broker-snapshot-reconciliation.md` | K0 | +22 | 4절(R6 신고) |
| `.gitignore` | K1 | +6 | 확인 기록, 결과 폴더, 종가 증거 폴더, 거래내역 증거 폴더 |
| `.claude/settings.json` | K2 | +4 −1 | deny 3줄 추가(3.7 g). 다른 줄 무변경 |

고치지 않은 것: `timing_engine.py`, `evaluate_alerts.py`, `SKILL.md`, `assets/locales/ko-KR.json`, `build_market_snapshot.py`, `references/yfinance-data.md`, acceptance 16개, `workspace/policies/` 전체, `portfolio_decision_dashboard.py`, `validate_research_packet.py`, 기존 테스트 파일 전부.

### 3.3 계획(2.2 "1차" 표)과 달라진 점

| 달라진 점 | 이유 |
|---|---|
| 대조 경로 4개 파일을 1차에서 고쳤다(2.2에서는 2차 7번) | P8-6 결정과 지침 8-5 |
| `scripts/cash_flow_evidence.py`, 분류 낱말표, 스키마 2개 추가 | 지침 8-5(거래내역 증거 파일 방식) |
| 스키마 3개 → 7개 | 기록 제안·payload, 거래내역 증거·신고 블록이 따로 필요했다 |
| `portfolio-status-ko-KR.json`, `holding-card-ko-KR.json` 무변경 | 문구를 새 locale 한 곳에 두었다 |
| 기존 테스트 파일 무수정, 표시 테스트는 새 파일 | 기존 단언을 그대로 두고 통과하는지로 "더하기만"을 보이기 위해 |
| 실행기 보완 3건(3.5) | 구현 뒤 자체 점검에서 나온 빈틈 |

### 3.4 구현하면서 정한 기본값 (D13~D30, 다르게 하려면 번호로 알려 달라)

r2·지시문에 글자로 없어서 Builder가 가장 좁은(멈추는) 쪽으로 정한 것이다. Judge가 볼 항목이다.

| # | 기본값 | 근거·영향 |
|---|---|---|
| D13 | V의 "세션 수"는 일간 수익률 개수다. 252개 수익률(종가 253개), 최소 60개 수익률(종가 61개) | "252세션 일간 수익률 표준편차"를 수익률 기준으로 읽음. 최소 쪽이 1세션 더 엄격하다 |
| D14 | 목표 비중은 0.1%p 눈금, 내림. 줄이기는 "예상 E ≤ 1.55인 가장 큰 눈금", 채우기는 "예상 E ≤ 1.55·상한·확인된 현금 안의 가장 큰 눈금" | 눈금 탐색이라 V가 비중에 대해 단조가 아니어도 결과가 정해진다 |
| D15 | 카드 ADD가 여럿이면 한 눈금씩 번갈아 올린다(합쳐서 예상 E ≤ 1.55) | 순서 편향 없이 합산 한도를 지킴 |
| D16 | 카드 ADD 종목이 있는데 전부 막히면 SOXL로 바꾸지 않는다 | "대체 없음"을 넓게 적용. 권고가 줄어드는 쪽 |
| D17 | 종목 상한 초과만으로는 줄이기 권고를 내지 않는다. 경고 + 그 종목 매수 차단이고, 줄이기 ①은 E ≥ 1.85일 때 나온다 | r2 `single_stock_cap_breach: block_new_buy_and_first_in_reduce_order`를 글자대로 |
| D18 | 원주가(adjusted=0)만 받는다. 세션 간 종가 비율이 0.5 이하이거나 2.0 이상이면 분할 가능성으로 보고 V 계산 불가(R0) | 전략 임계값이 아니라 자료 검사다. 3:2 분할은 못 잡는다(확인 필요) |
| D19 | 종가는 "달력이 ACTIVE"이고 "쪽 원문에서 다시 만들어지고" "봉 표기가 실측된 UTC 오프셋(−04:00)"일 때만 확인된 값이다. 아니면 값은 보이되 R0 | 7.2의 "9월분 달력 확인 필요", "서머타임 11/2 이후 확인"을 fail-closed로 |
| D20 | 쪽 파일의 가장 최근 봉은 아직 만들어지는 중일 수 있어 쓰지 않는다. 뒤 봉이 있어야 그 봉을 쓴다 | 장중 수집 방어 |
| D21 | 적용일 세션 자체도 선 판정을 한다 | 다시 확인한 HWM(9/30~적용일 고점)보다 이미 10% 아래면 L1이 바로 뜬다 |
| D22 | 실적 금지 구간 = 발표 세션 2세션 전 ~ 발표 뒤 첫 세션. 발표 시각이 장전이면 발표 세션까지, 장후·모름이면 다음 세션까지. 지난 실적일만 있으면 "미확인" | 기존 문장 규칙(`earnings_blackout_single_stocks`)을 세션 달력으로 계산 |
| D23 | 입출금 = 달러 예수금의 입금·출금·환전. 일부만 신고하면 남은 금액 때문에 보류가 이어진다. 증거 기간은 끊기면 안 되고(직전 기간 다음 날까지 시작) 대조일까지 닿아야 한다. 이미 신고된 줄은 다시 세지 않는다(거래일 + 거래번호) | 환전은 r2에 없지만 달러 자산에는 입출금과 같다 |
| D24 | 보유가 줄어든 대조가 들어오면 **날짜가 더 늦은** 다음 대조까지 선 판정 보류 + R0 | 지침 8-5의 기본 규칙. 같은 날 다시 대조해도 풀리지 않는다 |
| D25 | 확인 기록 제안은 60분 뒤 만료 | 대조안(15분)과 같은 방식, 검토 시간을 고려 |
| D26 | 보유하지 않은 신규 편입 종목은 R5 대상이 아니다(보유 중인 종목만) | r2 `applies_to: every_held_instrument` |
| D27 | "적용 시작" 기록은 한 번만. 두 개면 기록 손상으로 본다 | 다시 시작하려면 별도 설계가 필요하다 |
| D28 | 다시 계산한 선 발동과 맞지 않는 검토 기록(선·발동일·HWM)은 R0 | 계산과 기록이 어긋나면 멈춘다 |
| D29 | 대조 원장에서 되짚을 수 없는 구간(옛 형식 줄, 원장 밖 변경을 기록한 줄 이전)은 보유 이력이 없는 것으로 본다 | 그 구간의 세션은 "확인된 보유 없음"으로 선 판정이 멈춘다 |
| D30 | 운영 기본 경로가 아닌 입력(`--state` 등)으로 만든 결과는 모든 표시 줄 끝에 `[비표준 입력]`이 붙는다 | 시험용 입력으로 만든 결과가 카드에 섞이는 것을 드러냄 |

### 3.5 구현 뒤 자체 점검에서 고친 것

| # | 빈틈 | 고친 내용 |
|---|---|---|
| 1 | 미신고 대조 뒤, 그 기간을 다시 덮지 않는 다음 대조가 보류를 풀 수 있었다 | 증거 기간은 전액 신고된 대조에서만 앞으로 나간다. 테스트 `test_undeclared_deposit_holds_hwm_and_lines_and_pauses_recommendations` |
| 2 | 원장 사슬이 깨졌을 때 "원장 없음"으로 처리되어 이유 없이 통과했다 | 사슬 검사를 먼저 한다. 테스트 `test_broken_ledger_chain_is_not_trusted` |
| 3 | 종가 이력 파일의 값을 고치고 해시를 다시 계산하면 통과했다(쪽 해시만 대조) | 실행기가 쪽 원문에서 이력을 다시 만들어 저장된 이력과 같을 때만 쓴다. 테스트 `test_edited_history_with_a_recomputed_hash_is_not_reproducible_from_the_pages` |
| 4 | 실행기·이력 빌더에 달력 활성화 파일을 바꿔 끼우는 명령 인자가 있었다 | 인자를 없앴다. 달력 권한은 `workspace/policies/session_calendar_activation.json`만 본다. 이력 파일이 "ACTIVE"라고 적어도 실행기가 다시 판정한다. 테스트 `test_history_file_cannot_claim_an_active_calendar_or_verified_closes_by_itself` |
| 5 | 보유하지 않은 신규 편입 후보의 종가가 미확인이어도 권고가 나왔다 | 후보 종가도 확인돼야 한다. `CANDIDATE_CLOSE_UNVERIFIED` |

### 3.6 구현 중 새로 확인한 사실

| # | 사실 | 근거 | 처리 |
|---|---|---|---|
| F1 | Production ACTIVE 달력은 2026-08-29까지다. 9월 이후 종가는 지금 전부 "미확인"으로 나온다 | `workspace/policies/session_calendar_activation.json`(`coverage_end` 2026-08-29), 지시문 7.2 C11 | D19. 달력 활성화(2026 전체, artifact `2421eeb7…`)는 별도 K3. **끝나기 전에는 E와 선이 "미확인" 표시로만 나온다** → **2026-10-02 해소**: 2026 전체 달력은 이미 통합 Production 권한에서 ACTIVE였다. S7 코드가 옛 파일을 읽던 것을 통합 권한 연결로 고쳤다(`s7-calendar-binding-builder-prompt-2026-10-02.md`, 병합 `cd39212`) |
| F2 | 30분봉 원문에는 종목 필드가 없다 | 표본 2개(행 키 9개) | 쪽 폴더 이름 = 종목으로 묶는다(`PAGE_FOLDER_SYMBOL_MISMATCH`). 다른 종목 파일을 잘못 넣으면 못 잡는다(확인 필요) |
| F3 | `ust21100` 응답 최상위에 계좌 표시 `acnt_print`가 있다 | `kiwoom_api_spec.json` `ust21100` response | `normalize`가 복사하지 않는다(테스트 `test_account_label_is_never_copied`). 원문 파일은 정리 뒤 지우도록 절차에 적었다 |
| F4 | 실제 대조 원장 2줄은 모두 되짚어진다. 스냅샷 3개(revision 14·15·16, as_of 2026-08-14·09-29·09-29)가 나온다 | 원본 폴더 원장을 읽기만(수량·금액 미출력), 실행 전후 파일 해시 동일 | 9/30 세션은 revision 16 보유로 계산된다 |
| F5 | 값이 안 바뀌고 `as_of`도 같은 대조는 `NO_CHANGE_REQUIRED`라 적용되지 않는다. 그 대조에 붙인 신고 블록은 원장에 남지 않는다 | `scripts/kiwoom_broker_shadow.py`(status 결정) | 다음 대조의 증거 기간이 그 구간을 덮어야 한다. 절차 문서에 적음 |
| F6 | 정책 추가로 평가기 `rules_hash`가 `473e2dad…` → `ebf17aa1…`로 바뀐다. 기존 키 내용은 같아 shadow cohort 지문 재료(`strategy_version`, `holding_risk_rules`, `holding_timing_rules`)는 그대로다 | 4.6 | 1d에서 예측한 대로. 이벤트 중복 억제가 한 번 초기화된다 |

### 3.7 Judge 필수 수정 반영 (지시문 9.1, 2026-10-02)

- 순서: Judge 재현을 테스트로 작성 → 수정 전 코드에서 실패 확인 → 수정 → 통과.
- 재현 테스트 파일: `tests/test_portfolio_exposure_judge_fixes.py`(약칭 JF, 29개).
- 수정 전 실행: 27개 중 **20개 실패**(a 2, b 7, c 2, d 3, e 3, f 2, g 1). 나머지 7개는 "정상일 때는 통과한다"를 보는 대조용이다. e의 둘째 문장용 2개는 수정과 함께 더했다.
- 수정 뒤: 29개 모두 통과.
- 범위: 1차(더하기만) 그대로. 기존 정책 키·등록부·고정 파일 무변경(4.5·4.6 다시 확인).

| # | 재현 테스트(JF) | 고친 곳 | 고친 내용 |
|---|---|---|---|
| a | `FixAHeldFailsClosedTests.test_cash_flow_hold_lifted_by_a_reconciliation_dated_after_the_session`, `…test_sale_hold_lifted_by_a_reconciliation_dated_after_the_session`, 대조용 `…test_hold_is_lifted_once_the_session_reaches_the_later_reconciliation` | `scripts/portfolio_exposure.py:1012`, `:943-949` | 선 판정이 `HELD`면 R0(`hwm_line_or_pause_state_missing_or_corrupt`, 사유 `LINE_EVALUATION_ON_HOLD`)를 켠다. 평가 세션보다 날짜가 늦은 대조는 그 세션 판정에 쓰지 않는다(보류 해제도 인정하지 않음). 결과에 `snapshot.later_reconciliations_not_used`로 개수를 적는다 |
| b | `FixBActivationCandidateTests` 9개(`test_broker_reconciliation_older_than_four_days_is_not_ready`, `test_state_changed_outside_the_ledger_is_not_ready`, `test_unverified_closes_are_not_ready`, `test_closes_of_instruments_held_earlier_in_the_window_must_be_verified_too`, `test_v_unavailable_or_corrupt_journal_or_stale_session_is_not_ready`, `test_non_default_inputs_are_not_ready`, `test_journal_refuses_a_review_whose_candidate_was_edited_to_ready`, 대조용 `test_clean_inputs_are_ready`), RUN `test_non_default_inputs_are_labelled_and_cannot_start_activation`, `test_calendar_that_is_not_active_leaves_every_close_unverified` | `scripts/portfolio_exposure.py:562-585`(`activation_blockers`), `:588-632`(`activation_candidate`), `:996`, `:1028-1033`; `scripts/portfolio_review_journal.py:120-125` | 후보 `READY` 조건: "적용 시작 없음·기록 파일 없음" 말고 열린 R0 사유 0개, 창(9/30~평가 세션) 안에서 보유한 모든 종목의 종가가 확인됨, 기본 입력(`non_default_inputs` 비어 있음), 상태가 원장 줄로 확인됨. 아니면 사유를 달고 `NOT_READY`(HWM 값도 내지 않음). 기록 제안 때 결과 파일의 R0·입력으로 한 번 더 검사한다(`ACTIVATION_BLOCKED`) |
| c | `FixCHistoryGapTests` 5개(`test_one_missing_close_inside_the_window_makes_v_unavailable`, `test_missing_benchmark_close_inside_the_window_makes_v_unavailable`, `test_new_entry_candidate_with_a_gap_is_blocked`, 대조용 `test_gap_older_than_the_252_return_window_does_not_matter`, `test_short_history_label_is_only_for_a_late_start_without_gaps`) | `scripts/portfolio_exposure.py:180-205`(`common_window`), `:248-273`, `:291-293` | 창 = 평가 세션까지의 마지막 253세션. 단 종목별 "첫 종가"(상장·보관 시작) 가운데 가장 늦은 날보다 앞으로는 가지 않는다. 그 뒤에 빠진 종가가 있으면 창을 줄이지 않고 V 계산 불가(R0, `V_HISTORY_GAP:<종목>:<세션>`). "짧은 이력"은 누락 없이 시작이 늦을 때만 붙는다 |
| d | `FixDEvaluationSessionTests` 3개(`test_default_session_fails_when_the_calendar_does_not_cover_today`, `test_explicit_old_session_is_labelled_and_fails_closed`, `test_explicit_session_older_than_the_latest_completed_session_fails_closed`) | `scripts/run_portfolio_exposure_review.py:264-288`(`resolve_session`), `:345`, `:378`; `scripts/portfolio_exposure.py:942`, `:1329-1330`; locale `not_latest_session_suffix` | 달력이 오늘(미국 동부 날짜)을 덮지 못하면 기본 실행은 실패한다(`SESSION_CALENDAR_DOES_NOT_COVER_TODAY:<달력 끝>`, 결과 파일 없음). `--session`으로 옛 세션을 직접 주면 결과는 나오되 R0(`EVALUATION_SESSION_NOT_VERIFIED_LATEST` 또는 `EVALUATION_SESSION_NOT_LATEST:<최신 세션>`)이고 표시 줄 끝에 `[최신 세션 아님]`이 붙는다. 아직 끝나지 않은 세션은 거부 |
| e | `FixEPostActivationLedgerTests` 5개(`test_state_revision_after_activation_without_any_ledger_entry`, `test_missing_intermediate_revision_is_not_trusted`, `test_no_ledger_after_activation_is_not_a_pass_even_at_the_activation_revision`, `test_activation_cannot_be_proposed_for_a_state_without_a_ledger_entry`, 대조용 `test_revisions_confirmed_by_ledger_entries_are_evaluated`), `FixERunnerTests.test_runner_without_a_ledger_after_activation_fails_closed` | `scripts/portfolio_exposure.py:426-446`, `:1014-1015`, `:621-624` | 적용 시작 revision부터 지금까지의 모든 상태 revision이 되짚어진 원장 줄로 확인돼야 한다. 하나라도 아니면 선 판정을 하지 않고(HWM은 그대로, 현금 증가를 수익으로 넣지 않음) R0 두 개를 켠다: `hwm_line_or_pause_state_missing_or_corrupt`(`…REVISION_WITHOUT_LEDGER_ENTRY:<rev>`), `undeclared_cash_flow`(`CASH_FLOW_NOT_VERIFIABLE_WITHOUT_LEDGER_ENTRY`) |
| f | `FixFClassificationTests` 3개(`test_the_two_judge_strings`, `test_fee_tax_and_interest_words_are_not_external_flows`, 대조용 `test_plain_transfers_are_still_external_and_unknown_rows_still_stop`) | `assets/kiwoom-transaction-history-classification.json:13-17`, `scripts/cash_flow_evidence.py:38`, `schemas/kiwoom-cash-flow-evidence.schema.json:48` | 새 분류 `FEE_TAX_INTEREST`(입출금 아님). 낱말: 수수료, 세금, 제세, 세액, 원천징수, 이용료, 이자. 배당 다음, 환전·매매·입출금보다 먼저 본다. "수수료출금", "예탁금이용료입금"을 테스트로 고정. 맞는 규칙이 없는 줄은 전처럼 미분류로 멈춘다 |
| g | `FixGSettingsTests.test_claude_code_denies_journal_apply_and_direct_journal_edits` | `.claude/settings.json:19-21` | deny 3줄 추가: `Bash(*portfolio_review_journal.py apply*)`, `PowerShell(*portfolio_review_journal.py apply*)`, `Edit(/stock-strategy-system/decision_journal.json)`. 기존 줄은 그대로(테스트가 기존 8줄도 확인) |

함께 바뀐 것

| 파일 | 내용 |
|---|---|
| `schemas/portfolio-exposure-review.schema.json` | `snapshot.later_reconciliations_not_used`, `review_lines.ledger_unconfirmed_revisions` |
| `tests/s5_exposure_fixtures.py` | 스냅샷 기본값을 "원장 줄로 확인됨"으로(실제 대조와 같게). e 때문에 필요 |
| `tests/test_run_portfolio_exposure_review.py` | 운영 기본 경로·시계를 모듈 상수 패치로 바꿔 "기본 입력"으로 돌린다(명령 인자로는 적용 시작 불가). 상태 파일과 함께 원장 한 줄을 쓴다. 테스트 16 → 17개 |
| `references/portfolio-exposure-review.md` | 위 규칙, 적용 시작 조건·순서, 누적 파일 저장(9.2-4) |

Judge가 다시 볼 해석(글자로 정해지지 않아 Builder가 멈추는 쪽으로 정한 것)

| # | 해석 | 영향 |
|---|---|---|
| a | 날짜가 늦은 대조는 보류 해제뿐 아니라 보유·현금에도 쓰지 않는다 | 한국 오후에 대조하면(`as_of`가 다음 날) 직전 세션의 E는 그 전 대조의 보유로 계산된다. 대조 나이 4일 규칙은 그대로다 |
| b | "기본 입력"에 `--now`도 넣었다 | 시험용 시계로 만든 결과로는 적용 시작을 제안할 수 없다 |
| d | 달력이 오늘을 덮지 못할 때 기본 실행을 "실패"로 했다(R0 결과 대신) | 지금 ACTIVE 달력(8/29까지)에서는 `--calendar` 없이 돌리면 종료 코드 2다. U1(달력 활성화) 전에는 `--calendar`로 2026 전체 artifact를 줘야 하고, 그 결과는 달력 비ACTIVE라 "미확인"이다 |
| e | 둘째 문장("원장 없음은 통과가 아니다")을 "적용 시작 revision 자체도 원장 줄로 확인돼야 한다"로 구현했다. 적용 시작 후보도 원장 줄로 확인된 상태일 때만 `READY`다 | 실제 원장은 revision 16이 원장 줄에서 나오므로 조건을 만족한다(F4). 원장이 한 번도 없던 환경에서는 첫 대조 뒤에야 적용 시작이 된다 |
| f | 낱말 "세액"·"이자"처럼 짧은 말도 넣었다 | 입출금 줄을 수수료로 잘못 볼 위험보다 수수료 줄을 입출금으로 세는 위험을 더 크게 봤다. 실제 적요는 U3에서 확인 |

## 4. 검증

테스트 파일 약칭: JF = `tests/test_portfolio_exposure_judge_fixes.py`(3.7), PE = `tests/test_portfolio_exposure.py`, FC = `tests/test_portfolio_exposure_fail_closed.py`, CF = `tests/test_cash_flow_evidence.py`, CH = `tests/test_regular_session_close_history.py`, RJ = `tests/test_portfolio_review_journal.py`, RUN = `tests/test_run_portfolio_exposure_review.py`, DISP = `tests/test_portfolio_exposure_display.py`.

### 4.1 대상 테스트

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_<name>.py"`. "기준선"은 0.4의 미통과 ID 목록이다.

요구 8의 12개

| 테스트 | 실행 | 결과 | 기준선에 없는 새 미통과 |
|---|---|---|---|
| `test_timing_engine` | 8 | OK | 0 |
| `test_evaluate_timing_integration` | 10 | OK | 0 |
| `test_portfolio_decision_dashboard` | 306 | 미통과 188(실패 1 + 오류 187) | 0(기준선과 같은 ID) |
| `test_reconcile_broker_state` | 56 | OK | 0 |
| `test_build_holding_fact_pack` | 36 | OK | 0 |
| `test_holding_card` | 65 | OK | 0 |
| `test_v2_4_dual_phase` | 12 | OK | 0 |
| `test_v2_5_leveraged_confirmation` | 8 | OK | 0 |
| `test_v2_6_12_holding_valuation_shadow` | 88 | OK | 0 |
| `test_v2_6_3_free_web_new_buy` | 70 | OK | 0 |
| `test_v2_6_7_session_aware_kiwoom_priority` | 42 | 미통과 14 | 0(기준선과 같은 ID) |
| `test_v2_6_integration` | 15 | OK | 0 |

그 밖에 돌린 것: `test_validate_research_packet` 3(미통과 1, 기준선), `test_portfolio_decision_order_intent` 73(미통과 32, 기준선), `test_v2_4_automation` 6, `test_v2_2_tactical_radar` 17, `test_validate_decision_record` 3, `test_v2_5_broker_snapshot` 27, `test_v2_6_broker_beginner` 25, `test_portfolio_status` 13, `test_language_contract` 2, `test_v2_5_beginner_renderer` 43 — 모두 새 미통과 0.

새 테스트(170개, 전부 통과. 3.7 반영 뒤)

| 파일 | 개수 | 다루는 것 |
|---|---|---|
| PE | 43 | 정책 값 고정, N·V·E, 대역 경계, 줄이기 순서, 채우기, 실적 금지 구간, 신규 매수·교체 제안, 출력 권한 |
| FC | 32 | R4 선 경계, R6 보류, R5 고점, R0 트리거 7개 |
| CF | 19 | 거래내역 분류, 신고 한도, 대조안·apply·CLI |
| CH | 14 | 15:30 봉 선택, 조기 폐장, 쪽 검증, 달력 권한, 갱신 규칙 |
| RJ | 9 | 제안·확인 코드·사슬·만료 |
| RUN | 17 | 끝에서 끝까지(적용 시작 → 확인된 결과), 원장 되짚기, 변조 감지, 비표준 입력 |
| JF | 29 | Judge 필수 수정 a~g 재현(3.7) |
| DISP | 7 | fact pack 블록, 카드 머리말 한 줄 |

### 4.2 지시문 "테스트 사례" 대응표

| 사례 | 테스트 |
|---|---|
| 선 경계: 정확히 닿음 | FC `test_equity_exactly_on_the_line_triggers_and_one_cent_above_does_not` |
| 선 경계: 같은 하락 구간 1회 | FC `test_a_line_triggers_once_in_the_same_drawdown` |
| 선 경계: 새 HWM 재무장 | FC `test_a_new_hwm_rearms_the_line` |
| 선 경계: 검토 "계속" 뒤 다음 선 | FC `test_review_continue_keeps_the_hwm_and_the_next_line_still_triggers`, `test_l2_pause_is_released_only_by_a_matching_journal_review` |
| R0 트리거 7개 각각(채우기·신규 매수 멈춤, 줄이기·경고는 "미확인"으로 계속) | FC `test_1_exposure_or_equity_or_v_unavailable` ~ `test_7_undeclared_cash_flow`(7개), 기준 상태 `test_baseline_has_no_trigger_and_gives_an_add` |
| V 이력 부족: 60 미만 신규 편입 불가 | PE `test_new_entry_with_fewer_than_60_sessions_is_blocked` |
| V 이력 부족: 60~251은 가용 세션 | PE `test_history_of_60_to_251_sessions_is_used_and_labelled_short`, 보유 종목 60 미만은 `test_held_instrument_below_60_sessions_makes_v_unavailable` |
| 0.4배 초과와 줄이기 순서 | PE `test_cap_excess_first_then_card_trim_then_soxl`, `test_exactly_at_cap_is_not_a_breach`, `test_index_leveraged_etfs_are_exempt_and_dram_is_capped` |
| SOXL 없음 → "초과 미해소" 경고만 | PE `test_without_soxl_only_an_unresolved_warning_is_given`, `test_soxl_at_zero_still_above_target_warns` |
| 늘리는 권고의 예상 E > 1.55 또는 상한 초과 → 생략: 채우기 | PE `test_projected_exposure_above_target_omits_the_add`, `test_add_is_limited_by_verified_cash`, `test_card_add_stock_is_used_instead_of_soxl_and_is_capped` |
| 같음: 대역 안 신규 매수 | PE `test_new_buy_within_band_is_shown_only_when_projected_exposure_and_cap_hold`, `test_new_buy_above_the_single_stock_cap_is_omitted` |
| 같음: 교체 매수 쪽 | PE `test_swap_buy_leg_is_omitted_when_projected_exposure_or_the_cap_would_be_exceeded` |
| E ≥ 1.85 → 줄이기 + 신규 매수 멈춤 | PE `test_exactly_at_reduce_threshold_is_above_band`, `test_just_below_reduce_threshold_stays_in_band` |
| E ≥ 1.9 → 모든 신규 매수 차단 + 줄이기 "긴급" | PE `test_exactly_at_hard_ceiling_blocks_all_new_buys_and_flags_urgent` |
| SOXL이 R5로 멈춤 → 채우기 생략(대체 없음) | PE `test_soxl_paused_by_peak_review_omits_the_add_without_substitute` |
| 실적 금지 구간 | PE `test_window_is_two_sessions_before_through_first_session_after`, `test_stock_in_blackout_gets_no_add_recommendation` |
| 실적일 미확인 = 금지 구간 | PE `test_unverified_or_uncheckable_earnings_date_is_a_blackout` |
| MU 금지 구간에 DRAM 대체 금지 | PE `test_mu_blackout_blocks_dram_as_a_substitute` |
| 교체 두 단계(미체결 매도 대금은 현금 아님) | PE `test_swap_shows_the_sell_leg_first_and_withholds_the_buy_leg`, `test_swap_buy_leg_needs_verified_cash_not_expected_sale_proceeds`, `test_buy_leg_is_withheld_while_a_sale_is_waiting_for_cash_confirmation` |
| R5 기준 고점 없음 → 그 종목 채우기 멈춤 | PE `test_no_baseline_peak_pauses_the_add_for_that_instrument` |
| 입출금: 신고 한도 초과 거부 | CF `test_declaration_must_stay_within_the_unexplained_cash_change`, `test_over_limit_or_evidence_less_declaration_is_rejected_before_any_broker_read`, `test_apply_rejects_an_inconsistent_declaration_and_writes_nothing` |
| 입출금: 미신고 → HWM·선 보류 + 채우기·신규 매수 멈춤 | FC `test_undeclared_deposit_holds_hwm_and_lines_and_pauses_recommendations`, `test_undeclared_withdrawal_does_not_fire_a_false_line`, `test_reconciliation_without_cash_flow_evidence_is_on_hold`, `test_7_undeclared_cash_flow`, RUN `test_post_activation_reconciliation_needs_a_cash_flow_declaration` |
| 입출금: 배당·수수료·세금은 입출금 아님 | CF `test_rows_are_classified_and_only_deposits_withdrawals_and_fx_are_external`, FC `test_dividends_fees_and_taxes_are_not_cash_flows` |
| (R1) 미등록 상품 보유 → E 계산 불가 | PE `test_unregistered_holding_makes_exposure_unavailable`, FC `test_2_unregistered_instrument_held` |
| (R1) 미등록 상품 신규 매수 차단, MVLL·NBIL 신규 매수 불가 | PE `test_sell_only_and_unregistered_instruments_cannot_be_bought`, `test_new_buy_within_band_is_shown_only_when_projected_exposure_and_cap_hold`(MVLL·미등록 줄) |
| (R2) 상품 승인 게이트가 열린 뒤에도 매수 제안은 watch_only·B 이하, 후보 없음 | **2차**(게이트는 #12·#13에서 열린다). 1차에서 보이는 것: PE `test_output_is_target_weights_only_with_no_authority`(권한 3필드, 수량·후보 키 없음, 등급 B·C·D뿐), `test_first_stage_keeps_the_old_controls`(캐시 승인 값 전부 false 유지) |
| (R7) 은퇴 규칙이 알림을 내지 않고 gap·halt 감시는 남음 | **2차**(은퇴는 #1~#8·#13·#14). 1차에서 보이는 것: PE `test_first_stage_keeps_the_old_controls`, 4.1의 기존 12개 무변경 통과, 4.5(엔진·평가기 해시 동일) |

### 4.3 S6 필수 수정 5~11의 fail-closed 테스트

| # | 필수 수정 | 테스트 |
|---|---|---|
| 5 | 공통 fail-closed | FC `FailClosedTriggerTests` 7개, RUN `test_missing_or_unverified_closes_fail_closed_but_keep_values_visible` |
| 6 | 미등록 상품 배수 기본값 삭제 | PE `test_missing_or_inconsistent_policy_is_rejected_not_defaulted`, `test_unregistered_holding_makes_exposure_unavailable` |
| 7 | V 가격 출처·공통 창·조기 폐장일 봉 | CH `test_real_sample_picks_the_1530_bar_close_not_the_1600_bar`, `test_early_close_uses_the_bar_before_the_early_close`, `test_newest_bar_of_a_file_is_not_trusted_as_complete`, `test_missing_session_inside_the_range_is_reported_as_a_gap`, RUN `test_calendar_that_is_not_active_leaves_every_close_unverified`, PE `test_split_guard_makes_v_unavailable` |
| 8 | R6 미신고 시 채우기도 멈춤, 신고 한도, 배당·수수료 구분 | 4.2 입출금 3줄, CF `test_unknown_or_ambiguous_rows_are_unresolved`, `test_chain_requires_contiguous_coverage_up_to_the_reconciliation_date`, `test_rows_already_declared_are_not_counted_twice` |
| 9 | L2 신규 매수 멈춤, 늘리는 권고 예상 E ≤ 1.55, 연산자, policy_version | FC `test_review_continue_keeps_the_hwm_and_the_next_line_still_triggers`, 4.2의 "생략" 3줄, PE `BandTests` 4개(≥·≤ 경계), `test_real_policy_carries_the_fixed_r2_values` |
| 10 | R5 전향 기준 | FC `PeakReviewTests` 6개(`test_peak_is_forward_only_from_activation`, `test_close_gap_since_the_basis_date_is_unverified` 포함) |
| 11 | 줄이기 순서 | PE `ReduceOrderTests` 6개 |

### 4.4 스키마·등록부·배포 검증

| 검사 | 결과 |
|---|---|
| `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` | `PASS`, 오류 0(새 스키마 7개 포함, 3.7 뒤 다시 실행) |
| `validate_registry_consistency.py --registry workspace/policies/instrument_registry.json --policy stock-strategy-system/alert_policy.json` | `VALIDATED`, `canonical_sha256` `750a0b4b…e1dc`(0.2와 같음), 오류 0, 경고 0 |
| `validate_skill_deployment.py`(설치 폴더는 읽기만) | `PASS`. 6개 모두 원본 = 설치 = required = observed `MATCH`. 1차는 고정 파일을 고치지 않아 설치 스킬 동기화가 필요 없다 |
| 새 스크립트 ASCII | `test_language_contract`, `test_v2_5_beginner_renderer` 통과 |

### 4.5 고정 파일 해시 (0.3과 대조, `validate_skill_deployment.normalized_text_sha256`)

- `deployment_gate` 6개: 전부 0.3과 같음(`DAC71EA7…`, `66B52485…`, `D24D721C…`, `8EF03089…`, `32F36475…`, `5A0F54DE…`).
- 키움 acceptance 16개: 전부 0.3과 같음(`run_manual_portfolio_analysis.py` `BAEC1640…`, `tests/test_manual_portfolio_analysis.py` `7368D7C1…`, `kiwoom_runtime_bridge.py` `61DDF3FD…` 포함).
- 바뀐 고정 파일 0개(3.7 반영 뒤 다시 대조, 결과 같음).

### 4.6 키 경로 diff와 5절 r2 대응

`stock-strategy-system/alert_policy.json`(HEAD blob 대 worktree, JSON을 키 경로로 펴서 비교)

| 항목 | 값 |
|---|---|
| 더한 경로 | 177개(`portfolio_exposure_policy` 140, `portfolio_review_lines` 37) |
| 지운 경로 / 값이 바뀐 경로 | 0 / 0 |
| 최상위 키 순서 | 기존 순서 그대로, 두 섹션은 `alert_grades` 뒤·`archived_prior_strategy` 앞 |
| 새 섹션 2개를 뺀 `canonical_hash` | `ab297451…842e` = 변경 전(같음) |
| `canonical_hash` 전 → 후 | `ab297451…842e` → `fb2d3bba…15bb` |
| 원시 sha256(worktree, CRLF) 전 → 후 | `b8dd1b1a…` → `8e096514…` |
| LF 정규화 sha256 전 → 후 | `4a7c1492…` → `75d37fb0…` |
| git blob 전 → 후 | `3d9df21a…` → `0a405058…` |

`workspace/policies/instrument_registry.json`: 더한·지운·바뀐 경로 0. 원시 `f0c2a342…`, LF `8d11aae8…`, `canonical_hash` `750a0b4b…` 모두 0.2와 같음.

5절 r2 JSON 블록과 새 섹션의 대조(r2 블록을 파싱해 경로별로 비교)

| 섹션 | r2 경로 | 값까지 같은 경로 | 값이 다른 경로 | r2에 없는 경로 |
|---|---|---|---|---|
| `portfolio_exposure_policy` | 99 | 96 | 3 | 15 |
| `portfolio_review_lines` | 22 | 20 | 2 | 4 |

r2에서 빠진 경로는 없다. 다른 값과 r2에 없는 경로는 아래가 전부다.

| 경로 | r2 | 정책 | 이유 |
|---|---|---|---|
| 두 섹션의 `policy_version` | `2026-10-01-s5-final-proposal-r2` | `2026-10-01-s5-r2` | 지침 8-1, D8 |
| 두 섹션의 `status` | `proposed_not_applied` | `approved_display_only_old_controls_retained` | P6, 지침 8-1 |
| `add_recommendation_classification.instrument_approval_gate` | `opened_for_r3_instruments_via_canonical_registry` | `not_opened_in_first_stage_pending_canonical_registry_update` | D9(1차에서는 게이트가 열리지 않으므로 사실이 아닌 문구를 두지 않음) |
| `first_stage_scope` | — | 옛 통제 유지 설명 | P0 |
| `sox_equivalent.bar_label_basis`, `.latest_close_bar_definition`, `.close_label`, `.reference_close_use` | — | 봉 표기 기준(시작 시각, ET), P3 정의, "근사 종가", 참고 종가는 차이 표시만 | 지침 8-2(`latest_close_bar` 값은 그대로) |
| `sox_equivalent.short_history_rule` | — | 가용 세션(최소 60)을 보관 한계에도 적용 | P4-2, 지침 8-3 |
| `sox_equivalent.price_history_collection` | — | Cowork 저장 쪽 + repo 검증 | P4-1, 지침 8-4 |
| `alert_grade_mapping.*`(7개) | — | L1 C, 멈춤 있는 선 D, 1.9 D, 1.85 B, R5 B, R0 B, 채우기 B | P2. 코드는 이 값을 읽는다(코드에 등급 상수 없음) |
| `shadow_candidates.K132-G.implementation` | — | 설정만, 원장은 별도 K2 | P7 |
| `portfolio_review_lines.activation` | — | 사용자 확인 "적용 시작" 기록 | P6 |
| `portfolio_review_lines.state_storage` | — | 매번 재계산, 사람 확인만 기록 | P1 |
| `portfolio_review_lines.cash_flow_evidence` | — | Cowork 저장 `ust21100` 거래내역 | 지침 8-5 |
| `portfolio_review_lines.sale_proceeds_pending_rule` | — | 더 늦은 날짜의 대조까지 선 판정 보류 | 지침 8-5 |

값 고정 확인(테스트 `test_real_policy_carries_the_fixed_r2_values`): 1.55, 1.85, 1.25, 1.9, 0.4, 0.30, L1 0.90·L2 0.80·이후 0.10 간격, HWM 28473.94(2026-09-30), V 창 252·최소 60, `broker_snapshot_max_age_calendar_days` 4.

### 4.7 전체 테스트 (서브에이전트)

- 명령: `python -m unittest discover -s manage-us-stock-strategy/tests`.
- **최종(3회차, 3.7 Judge 수정 반영 뒤): `Ran 2228 tests in 87.081s`, `FAILED (failures=23, errors=291, skipped=1)`.**
- 2회차(3.5 보완 반영 뒤, Judge 판정 대상): `Ran 2198 tests in 82.466s`, `FAILED (failures=23, errors=291, skipped=1)`, 새 미통과 0.
- 최종 미통과 314개 = 기준선 314개. **기준선에 없는 새 미통과 ID 0개**, 기준선에서 사라진 ID 0개, 종류(FAIL ↔ ERROR)가 바뀐 ID 0개.
- 테스트 수 2058 → 2228(+170, 전부 새 테스트).
- 1회차(보완 전): `Ran 2195 tests`, 미통과 314, 새 미통과 0.
- 미통과 ID 목록: `docs/claude/s7-builder-stage4-test-failures-2026-10-01.txt`(기준선 파일과 같은 형식, 3회차 결과로 다시 씀).
- 테스트가 worktree에 남긴 파일 없음(실행 뒤 `git status`에 새 항목은 위 목록 파일뿐).
- 예상 실패(2.6): 1차는 없음. 실제로도 없다.

### 4.8 줄바꿈

고친 기존 파일 12개(`.claude/settings.json` 포함) 모두 CRLF만 있다(LF 단독 줄 0, BOM 없음). 줄 수가 늘어난 만큼만 CRLF가 늘었다(예: `alert_policy.json` 797 → 958). 새 파일은 LF로 썼다. 일괄 변환은 하지 않았다.

## 5. 보고

### 5.1 한 일

1차 범위를 구현했다. 새 계산·종가 증거·입출금 증거·사람 확인 기록·표시를 **더했고**, 옛 통제(원가 한도, 축소 슬롯, weakness_10ema, 재무장)와 상품 등록, 고정 파일은 그대로다. 정책 변경은 새 섹션 2개 추가뿐이다. 커밋하지 않았다.

바뀐 파일과 K 등급은 3.2, 키 경로 diff는 4.6, 해시 전후는 4.5·4.6, 테스트는 4.1~4.7에 있다.

### 5.2 지금 병합하면 실제로 보이는 것

- 종가 증거가 없는 지금은 노출 점검을 돌려도 E가 "미확인"(계산 불가)으로만 나온다. 권고는 하나도 나오지 않는다.
- 종가 증거를 넣으면 E(= max(N, V)), 줄이기 권고(목표 비중), 종목 상한 경고가 나온다. 다만 아래 2·3이 풀리기 전에는 **모든 값에 "미확인"이 붙고 채우기·신규 매수 권고는 멈춘다.** 순서대로 풀어야 한다.
  1. 종가 증거 수집(Cowork).
  2. Production 달력이 8/29까지다(F1). 달력을 활성화하기 전에는 기본 실행이 실패하고(3.7 d), `--calendar`로 2026 전체 달력을 주면 값은 나오되 "미확인"이다.
  3. "적용 시작" 기록이 없다(P6대로, 준비가 끝나기 전에는 선이 돌지 않는다).
- 옛 알림(원가 한도 D, 축소 슬롯 검토)은 그대로 나온다. 예약 평가기는 바뀌지 않았다.

### 5.3 확인 필요

| # | 내용 | 영향 | 누가 |
|---|---|---|---|
| U1 | **달력 활성화(2026-09 이후)**: ACTIVE 달력이 2026-08-29까지다 | 끝나기 전에는 E·선 전부 "미확인"(F1, D19) | 사용자·별도 K3 → **2026-10-02 해소**: 2026 전체 달력은 이미 통합 Production 권한에서 ACTIVE였다. S7 코드가 옛 파일을 읽던 것을 통합 권한 연결로 고쳤다(`s7-calendar-binding-builder-prompt-2026-10-02.md`, 병합 `cd39212`) |
| U2 | 서머타임 뒤 봉 표기(2026-11-02 이후) | 그날부터 종가가 "미확인"이 된다. 확인되면 `LABEL_VERIFIED_UTC_OFFSETS`에 `-05:00` 추가(K2) | Cowork 실측 → Builder |
| U3 | `ust21100` 실제 문자열: 입출금·환전의 `rmrk_nm`(적요) 낱말, 환전 줄의 통화코드, `deal_no`가 날짜 안에서 고유한지, `deal_dt`가 한국 날짜인지 | 낱말표가 맞지 않으면 "분류 못 함"으로 멈춘다(fail-closed). 환전 방향(매수 = 달러 유입)은 추정이다 | Cowork(금액 가린 표본) → **2026-10-02 실측**: 입출금·환전 실제 행 없음(확인 불가), 막힘 3건 → K2 후보(`s7-u3-transaction-history-measurement-2026-10-02.md`) |
| U4 | 거래내역 여러 쪽 수집이 끝까지 됐는지(연속조회)는 파일에서 알 수 없다 | 빠진 줄이 있으면 미신고 입출금을 놓친다 | Cowork 절차 |
| U5 | 분할·병합: 원주가만 받는다. 0.5 이하·2.0 이상만 잡는다 | 3:2 분할 같은 경우 V가 틀린다. 분할 뒤 이력 다시 받는 절차 없음 | 별도 K2 → **2026-10-02 해소**: MVLL 6/26 3:1 정분할 공식 확인(GraniteShares 6/12 보도자료). 사용자 A안(공식 분할 기록 파일 + V·고점 점검만 보정, 자산은 원주가, 작은 분할은 루틴 확인). `s7-split-adjustment-builder-prompt-2026-10-02.md`, 병합 `094dce7`, 기록 파일 `workspace/outputs/regular-session-closes/corporate-actions.json`(git 제외) |
| U6 | 키움 분봉이 통합 체결이 아닐 수 있다(7.1), 거래 적은 종목은 15:30 봉이 없을 수 있다 | 봉이 없으면 그 세션은 "누락"(R0) | Cowork 관찰 |
| U7 | 실적일 입력(`--earnings`)은 Cowork가 주는 파일을 그대로 믿는다 | "VERIFIED"라고 적으면 금지 구간이 풀린다. 기존 이벤트 증거 경로와 잇는 일은 범위 밖 | 2차 또는 별도 K2 |
| U8 | 30분봉 원문에 종목 필드가 없다(F2) | 다른 종목 파일을 폴더에 잘못 넣으면 못 잡는다 | Cowork 절차 |
| U9 | 원본 폴더의 정책 파일은 CRLF·LF 혼합이다(0.2). 병합하면 git이 파일을 다시 쓴다 | 원시 바이트 해시가 내용과 무관하게 달라질 수 있다(1d) | 병합 때 확인 |
| U10 | 기준선의 실패 22/오류 292 대 23/291 차이(0.4) | 합계는 같다. 원인은 보지 않았다 | — |
| U11 | 대조안 스키마에 선택 속성을 더하면서 버전 문자열(`kiwoom-reconciliation-1.0`)은 그대로 두었다 | 옛 대조안은 그대로 유효. 버전을 올리는 쪽이 맞는지는 Judge 판단 | Judge |
| U12 | 픽스처로 복사한 표본 2개의 커밋 승인 | 표본 README가 "커밋 전 별도 승인"이라 적었다 | 사용자 |

### 5.4 병합 뒤 작업 (P6 + 지시문 9.2, Builder는 하지 않는다)

순서가 중요하다. "적용 시작" 기록은 아래 1~6이 끝난 뒤에 한다(9.2-1).

1. 사용자: Judge 재확인 뒤 커밋·병합 승인.
2. 사용자·별도 K3: 세션 달력 활성화(U1). 그 전에는 기본 실행이 실패하고, 적용 시작 후보도 `NOT_READY`다. → **2026-10-02 해소**: 2026 전체 달력은 이미 통합 Production 권한에서 ACTIVE였다. S7 코드가 옛 파일을 읽던 것을 통합 권한 연결로 고쳤다(`s7-calendar-binding-builder-prompt-2026-10-02.md`, 병합 `cd39212`). 병합 뒤 원본 폴더 기본 실행에서 달력 ACTIVE·평가 세션 2026-10-01 확인.
3. Cowork: 30분봉 수집(SOXX + 보유 종목, 2026-04-01부터) → `regular_session_close_history.py build`. → **2026-10-02 완료**: 4종목(SOXX·SOXL·MVLL·NBIS) 각 27개 쪽 파일, 이력 4개 127세션(4/1~10/1) CONTIGUOUS·달력 ACTIVE·verify OK. `--pages 0`은 429로 실패해 3쪽씩 나눠 받음(`workspace/outputs/regular-session-closes/collect_30m.ps1`, git 제외). kiwoomcli 원본 형식을 읽도록 K2 수정(`s7-cli-page-shape-builder-prompt-2026-10-02.md`, 병합 `09a6298`). 새 막힘: V가 `SPLIT_GUARD:MVLL:2026-06-26`으로 계산 불가(키움 수정주가 주봉 기준 3:1 분할로 보임, 공식 확인 필요) → 6번 READY 전에 분할 처리 결정 필요. → 2026-10-02 공식 3:1 정분할 확인, 사용자 A안 선택, K2 지시문 `s7-split-adjustment-builder-prompt-2026-10-02.md`.
   - 받은 결과는 **누적 파일 하나**로 저장한다. 100행 쪽을 따로 저장하면 옛 쪽의 첫 봉이 버려진다(D20, 9.2-4).
   - 쪽 폴더 이름이 곧 종목이다. 다른 종목 파일을 넣어도 코드는 못 잡으니 절차로 막는다(F2, 9.2-4).
4. Cowork: U3 실측(`ust21100` 적요 낱말, 환전 방향, 통화코드, `deal_no`, 날짜 기준). 낱말표가 맞는지 확인한 뒤 거래내역 증거 절차를 시작한다(9.2-1, 9.2-3). → **2026-10-02 실측**(`s7-u3-transaction-history-measurement-2026-10-02.md`): 2025-01~2026-10 실제 입출금·환전 행 없음 → 그 낱말·통화코드는 확인 불가(추정 유지). `deal_no`는 날짜별 번호(관측 중복 0), `deal_dt`는 한국 처리·결제 반영일로 보임. 막힘 3건: 빈 기간(501724) 실패, `병합단주대금입금(외화)` → DEPOSIT 오분류, 액면분할·병합 입출고 → UNCLASSIFIED. K2 수정 뒤 증거 절차 시작. 사용자 권장안 승인, K2 지시문 `s7-u3-cash-flow-evidence-builder-prompt-2026-10-02.md`.
5. Cowork: 브로커 대조를 새로 한다(마지막 확인 9/29, 4일 기준). 적용 시작 뒤의 대조에는 매번 거래내역 증거를 붙인다.
6. Cowork: `run_portfolio_exposure_review.py`(기본 입력) → 후보가 `READY`인지 확인. → **2026-10-02 READY**(병합 `094dce7` 뒤, 분할 기록 OK): 사유 없음, 적용 시작 후보일 2026-10-01, HWM 29127.99(정책 시작값 +654.05), E 2.91(N 2.29, V 2.91, 수익률 126개 짧은 이력, HARD_CEILING), `non_default_inputs` 비어 있음, 달력 LOADED, 스냅샷 9/29(2일). 표시 전용 줄이기 권고 MVLL·SOXL(긴급). 4·5번(U3 실측, 새 브로커 대조)은 아직이다. READY는 실행 시점 값이라 7번 직전에 다시 확인한다.
7. Cowork: `portfolio_review_journal.py propose-activation` → 사용자 `확인 <코드>` → `apply`("적용 시작" 기록).
8. Cowork: 보유 종목 기준 카드 1회(R5).
9. 이후 매 세션: 30분봉 수집(누적 파일) → 이력 `--update` → 대조(거래내역 증거 + 신고) → 노출 점검.
10. Cowork: U2 실측(서머타임 뒤 봉 표기, 2026-11-02 이후).
11. 배포: 예약 런타임 배포는 급하지 않다(예약 평가기 무변경). 배포할 때 manifest 재생성(`alert_policy.json` 원시 해시가 바뀜). 배포하면 `rules_hash`가 바뀌어 옛 알림 중복 억제가 한 번 초기화되고, 같은 알림이 한 번 더 올 수 있다(F6, 9.2-6).

이번에 넣은 것(전에는 병합 뒤 작업이었음): `portfolio_review_journal.py apply`와 `decision_journal.json` 직접 편집 deny(3.7 g). `CLAUDE.md` 문장 추가는 사용자 판단으로 남긴다.

별도 작업으로 남긴 것(9.2, 이번에 구현하지 않음)

| # | 내용 | 등급 |
|---|---|---|
| 9.2-2 | 확인 기록의 **마지막 줄** 손편집은 사슬로 못 잡는다. 실행마다 다시 계산해 기록과 다르면 R0로 하는 검사(D28과 같은 규칙)를 넓힌다 | 별도 K2 |
| 9.2-3 | 거래내역 증거는 원문을 지우므로 재현할 수 없다. 대조의 예수금 변화와 교차 확인하는 설계 | 별도 설계 |
| 9.2-5 | 결과 스키마 권고 항목의 `additionalProperties`, 세션 불일치 표시, `--earnings` 파일 검증(U7), 분할 처리(U5) | 별도 K2 |

### 5.5 Judge가 볼 곳

| # | 볼 것 | 위치 |
|---|---|---|
| J1 | "더하기만"인가: 기존 정책 키·등록부·고정 파일 무변경 | 4.5, 4.6 |
| J2 | 대조 apply 경로 변경이 옛 동작을 바꾸지 않는가(블록이 없으면 대조안·원장 줄이 이전과 같은가, 상태 필드가 늘지 않는가) | `scripts/kiwoom_broker_shadow.py`, `scripts/apply_user_confirmed_broker_snapshot.py`, CF `ReconciliationIntegrationTests` |
| J3 | 새 쓰기 경로(확인 기록)의 통제: 확인 코드·사용자 메시지·만료·사슬·기록 머리 일치 | `scripts/portfolio_review_journal.py`, RJ |
| J4 | fail-open 여부: R0 7개, 보류 규칙, 3.5의 5건, 3.7의 a~f | FC, RUN, JF |
| J5 | Builder가 정한 기본값 D13~D30, 특히 D17(상한 초과만으로는 줄이기 권고 없음), D23(환전 포함·일부 신고), D24(매도 뒤 보류) | 3.4 |
| J6 | r2에 없는 정책 경로 19개와 값이 다른 5개 | 4.6 |
| J7 | 연산자: `≥`·`≤`·반올림 전 비교 | `scripts/portfolio_exposure.py`의 `_gte`·`_lte`·`evaluate_review_lines`, PE `BandTests`, FC `ReviewLineBoundaryTests` |
| J8 | 출력에 수량·금액·주문 지시가 없는가 | `schemas/portfolio-exposure-review.schema.json`, PE `OutputAuthorityTests` |
| J9 | 거래내역 분류 낱말표(추정 포함) | `assets/kiwoom-transaction-history-classification.json`, U3 |
| J10 | 4.2에서 2차로 넘긴 사례 2개(R2 게이트, R7 은퇴)가 1차 범위 밖이 맞는가 | 4.2 |

### 5.6 2차로 남은 것

#1~#8·#13·#14(옛 통제 은퇴), #12(등록부, SEC 1차 출처 확인), `timing_engine.py`·`evaluate_alerts.py`와 `deployment_gate`(P5), `validate_research_packet.py`, P8-1~5(universe, 위험 한도표, 신원·시세 범위, cohort 이관, BE·DRAM 신원), `alert_grades.D` 문장 보강(P2), 새 섹션 `status` → `approved_display_only`, K132-G 원장(별도 K2), 예약 작업 연결.

Builder 완료, worktree s7-policy, 새 실패 수 0

Builder 수정 완료, worktree s7-policy, 새 실패 수 0
