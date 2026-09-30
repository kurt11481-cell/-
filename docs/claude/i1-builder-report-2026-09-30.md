# I1 카드 코드화 Builder 보고서 (S7a, K2)

- 작성일: 2026-09-30
- 브랜치: `worktree-card-v1`, BASE `0ac9212` (S6 I7 병합). 커밋 안 함, push 안 함. 커밋은 사용자 승인 뒤.
- 설계: P3 §5-1~5-4(a′), P4 §4 S7a, G3 결정 6건(P4 §9). 지시문: P4 부록 A5와 사용자 추가 조건 7개.
- 변경 등급: K2(신규 스크립트·스키마·검증기). 고정 파일 16개, `portfolio_decision_dashboard.py`, `render_beginner_portfolio_report.py`, 정책 파일, 상태 파일, `SKILL.md`, `run_manual_portfolio_analysis.py`는 수정하지 않았다.

## 1. 변경 파일

| 파일 | 구분 | 내용 |
|---|---|---|
| `manage-us-stock-strategy/schemas/holding-card.schema.json` | 신규 | plan의 필드 이름(`evidence_binding`, `positions[action, rationale, thesis_kill, material_risk]`)만 빌린 별도 카드 스키마. `plan_status`, `order_intent_terms`, `proposed_quantity`, `limit_price`, `target_weight_pct` 없음 |
| `manage-us-stock-strategy/scripts/build_holding_fact_pack.py` | 신규 | 결정론 fact pack 생성기. 시계를 읽지 않는다 |
| `manage-us-stock-strategy/scripts/validate_holding_card.py` | 신규 | 카드 검증기(거부 7가지 + G3 결정 4 태그 검사 + 종목 집합 검사) |
| `manage-us-stock-strategy/scripts/render_holding_cards.py` | 신규 | 검증 통과 카드 → md(머리말 5줄 + 종목 카드 11칸 표) |
| `manage-us-stock-strategy/assets/locales/holding-card-ko-KR.json` | 신규 | 렌더러 한글 문구(스크립트는 ASCII 전용 규칙을 따름) |
| `manage-us-stock-strategy/tests/test_build_holding_fact_pack.py` | 신규 | 36건 |
| `manage-us-stock-strategy/tests/test_holding_card.py` | 신규 | 65건 |
| `.gitignore` | 수정 | `workspace/outputs/holding-cards/` 1줄(CRLF 유지, diff +1) |

신규 파일은 LF다(저장소 index가 LF이고 worktree 체크아웃만 CRLF). 기존 파일의 줄바꿈은 바꾸지 않았다.

## 2. 사용 방법

```text
python manage-us-stock-strategy/scripts/build_holding_fact_pack.py --analysis <manual-portfolio-analysis.json> --output-dir workspace/outputs/holding-cards/<날짜> [--alert-result <최근 알림 결과 json>]
(Cowork가 같은 폴더에 card.json을 쓴다)
python manage-us-stock-strategy/scripts/validate_holding_card.py --card <card.json> --fact-pack <fact-pack.json>
python manage-us-stock-strategy/scripts/render_holding_cards.py --card <card.json> --fact-pack <fact-pack.json>
```

- fact pack은 `--output-dir`이 스크립트가 있는 저장소의 `workspace/outputs/holding-cards/` 아래일 때만 쓰고, 이미 있으면 덮어쓰지 않는다(create-only). 파일럿처럼 같은 날 다시 만들려면 `2026-09-30-r2` 같은 새 폴더를 쓴다. `portfolio_status.py`의 `latest_card`가 이 날짜 폴더 이름을 읽는다.
- 카드 JSON의 `fact_pack_sha256`은 fact pack의 정렬 JSON 해시(`validation_common.canonical_hash`)다. 생성기가 출력하는 `fact_pack_sha256`을 그대로 쓴다. 파일 바이트가 아니므로 줄바꿈에 영향받지 않는다.
- 상태 파일, 정책 파일, baseline, 분석 JSON은 읽기만 한다. 쓰기 경로는 fact pack과 md 두 파일뿐이다.

## 3. 규칙 결과: 사용한 기존 함수

새 규칙을 구현하지 않았다.

| 용도 | 함수 | 호출 방식 |
|---|---|---|
| 손실 한도 기준가 | `evaluate_alerts.exact_loss_boundary(평단, 한도비율)` | `evaluate_alerts.py:768`, `portfolio_decision_dashboard.py:518`과 같은 호출. 평단은 분석 JSON의 `system_portfolio_state.average_cost_usd`(알림 엔진과 같은 출처) |
| 위반 판정 | `close <= boundary` | `evaluate_alerts.py:770`, dashboard `:523`과 같은 비교. `close`는 확정 정규장 종가만 쓴다 |
| 규칙 출처·승인 상태 | `portfolio_policy_gates.hard_risk_rule_audit(policy, ticker)` | 규칙 ID, 승인 상태, `action_on_breach`, `policy_authority_status` |
| 위반 상태 라벨 | 알림 엔진과 같은 조건 | `POLICY_AUTHORITY_UNVERIFIED` / `HARD_RISK_BREACH` / `NO_HARD_RISK` |

- **새로 둔 산술은 한 줄이다:** 남은 거리 = `boundary / close - 1`. 기존 함수에 "남은 거리"가 없어 `return_from_cost = close / avg - 1`(`evaluate_alerts.py:769`)과 같은 종류의 표시용 산술로 두었다. 파일럿 r2의 수기 산술과 같은 정의다.
- **확정 종가 선택:** 일봉 `records`에서 `reported_session == expected_completed_us_session`, `market_session_type == REGULAR_COMPLETED`, `price_basis == RAW_REGULAR_SESSION_CLOSE`, `bar_finalized`, `hard_risk_authority`가 모두 참인 마지막 레코드. 없으면 손실 한도는 `NOT_EVALUATED`(마크 가격으로 대신 계산하지 않는다).
- **프리마켓 마크는 참고값:** `premarket_reference_remaining_pct`로만 싣고 `REFERENCE_ONLY_NOT_HARD_RISK_AUTHORITY` 라벨을 붙인다.
- **timing:** 정책에 timing 규칙이 없으면 `NOT_APPLICABLE`. 있으면 알림 결과 파일(선택 입력)에서 `us_session_date`가 분석의 확정 세션과 같고 `event_type == holding_timing_review`인 후보가 있을 때만 `EVALUATED`. 파일이 없거나 오래됐거나 후보가 없으면 `NOT_EVALUATED`로 드러낸다(후보 없음을 "이상 없음"으로 읽지 않는다). 알림 결과 파일에서는 `us_session_date`, `candidates[].symbol/event_type/side/grade` 키만 읽는다.
- **규칙 방향(`rule_direction`):** 손실 한도 위반 또는 timing `reduce` 또는 정책 `default_direction=reduce` → `REDUCE`. 정책 `default_direction=hold` → `HOLD`. 그 밖은 `NONE`(반대할 규칙 없음).

### 실제 데이터 1회 대조 (읽기 전용, 파일럿 r2 분석 `manual-20260930T112114979550Z-f84117fcf3f5`)

| 종목 | 남은 거리 | 파일럿 수기값 | 프리마켓 참고 | 비중 | 평가손익률 |
|---|---|---|---|---|---|
| MVLL | -53.0% | -53.0% | -52.3% | 49.9% | -16.2% |
| SOXL | -32.9% | -32.9% | -31.5% | 38.8% | +16.8% |
| NBIS | -18.5% | -18.5% | -19.6% | 11.3% | +12.0% |

- 기준선 MVLL $16.71164(파일럿 $16.71), 현금 비중 0.02%, 주문가능현금 `VERIFIED_ORDERABLE_CASH` 라벨, 세 종목 모두 위반 아님. 같은 입력으로 두 번 만든 fact pack의 해시가 같았다.
- 확신도 상한: `LOW`, 사유 `EVIDENCE_GRADE_NOT_ALLOWLISTED`, `PREFLIGHT_NOT_PASS`(파일럿과 같다).
- 파일럿 판단(MVLL TRIM `TRIM_CONCENTRATION` / SOXL HOLD / NBIS HOLD, 확신도 낮음)으로 카드를 만들어 검증 오류 0건, 렌더 정상(머리말 + 카드 3장). 결과물은 scratchpad에만 두었고 저장소에는 쓰지 않았다.
- 비교에 쓴 원본 폴더 파일은 읽기만 했다(분석 JSON, 상태, 정책, baseline). 원본에는 쓰기도 git도 하지 않았다.

## 4. 사용자 결정 반영

| 조건 | 구현 |
|---|---|
| G3 형식(현행 = 파일럿 카드) | 머리말 5줄(결론 1·2, 상태, 노출, 확인할 것) + 종목 카드 11칸(규칙 결과, 판단, 현금·대안 대비, 숫자, thesis, 틀릴 수 있는 이유, kill 기준, 다음 이벤트, 판단이 바뀌는 조건, 데이터 상태, 지난 판단 성과) |
| 시장 환경 메모(선택) | `header.market_environment`가 있으면 `EXTERNAL_REFERENCE` 라벨 줄로 붙이고, 없으면 "시장 환경: SAVE 미입수". 카드 작성을 막지 않는다 |
| 수량·금액은 표시 전용 | fact pack `holding_observed`(display-only)와 `display` 블록에만 있다. 카드 `numbers`는 이 값과 일치해야 한다(거부 ⑥). 금지 키는 재귀로 거부한다(거부 ①) |
| 주문가능현금 | `VERIFIED` 여부 라벨과 함께 싣고 `expected_sale_proceeds_counted_as_orderable_cash: false` 고정 |
| 확신도 상한 = 허용목록 | 아래 §6 확인 필요 1번 |
| TRIM·EXIT 태그, HOLD `review_required`, ADD는 없음 | 스키마에 태그 enum, 검증기가 교차 규칙 검사(`REASON_TAG_*`, `HOLD_REVIEW_FLAG_*`). sidecar `DECISION_ACTIONS` 대응은 S7b이며 수정하지 않았다 |
| dashboard 제외 | 카드 스키마에 plan 전용 필드 없음. dashboard는 import만 했고 수정하지 않았다 |

## 5. 검증기 거부 목록 (S7a 완료 기준 7가지 + 추가)

| # | 코드 | 조건 |
|---|---|---|
| 1 | `ORDER_FIELD_FORBIDDEN:<경로>` | 금지 키(`order_intent_terms`, `proposed_quantity`, `limit_price`, `target_weight_pct`, `plan_status`, `order_type`, `time_in_force`, `stop_price`, `order_quantity`, `execution_quantity`)와 "주문·매매 계열 토큰 + 수량·금액 계열 토큰" 조합(`buy_quantity`, `sell_shares`, `trade_amount` 등), 한글 `주문`·`매수`·`매도` 포함 키를 어느 깊이에서든 거부. `held_quantity`, `weight_pct`, `loss_limit_remaining_pct` 등 표시용 이름은 허용 |
| 2 | `JUDGMENT_EMPTY:<종목>` | 행동·이유·확신도가 비었거나 공백뿐 |
| 3 | `WITHHOLD_NOT_ALLOWED:<종목>` | `WITHHELD`인데 fact pack의 `withhold_allowed`(`BROKER_UNAVAILABLE`은 브로커 상태가 `UNAVAILABLE`일 때, `IDENTITY_UNVERIFIED`는 종목·전체 identity 미검증일 때)가 허용하지 않음. 다른 행동에 `withheld_reason`이 붙어도 거부 |
| 4 | `RULE_DISAGREEMENT_UNLABELED:<종목>` | 규칙 방향과 다른 행동인데 `rule_agreement=DIFFERENT`와 비어 있지 않은 `rule_disagreement_reason`이 없음. 반대로 같은데 `DIFFERENT`이면 `RULE_AGREEMENT_LABEL_MISMATCH` |
| 5 | `CONVICTION_CAP_VIOLATION:<종목>` | fact pack 상한이 `HIGH`가 아닌데 확신도가 `LOW`가 아님. 상한 정보가 없으면 `LOW`로 본다(fail-closed) |
| 6 | `NUMBER_MISMATCH:<종목>:<필드>` | `numbers`의 11개 필드 중 하나라도 fact pack `display`와 다름(정확 비교, null도 일치해야 함) |
| 7 | `RUN_ID_MISMATCH`, `AS_OF_MISMATCH`, `FACT_PACK_HASH_MISMATCH` | 바인딩·해시 불일치. 같은 시각이면 표기 형식이 달라도 허용 |
| 추가 | `REASON_TAG_MISSING/INVALID/NOT_ALLOWED`, `HOLD_REVIEW_FLAG_MISSING/NOT_ALLOWED`, `TICKER_SET_MISMATCH`, `MARKET_ENVIRONMENT_LINES_MISSING`, `FACT_PACK_INVALID`, `CARD_SCHEMA_INVALID` | G3 결정 4 태그, 종목 집합 일치 등 |

## 6. Builder 판단과 확인 필요 (Judge 확인 대상)

1. **확신도 상한 해제 등급 = `GRADE_A`, `GRADE_B`.** 분석 스키마의 `evidence_grade` enum은 `GRADE_A`, `GRADE_B`, `UNVERIFIED` 세 값이다. 어느 값이 "낮지 않음"인지 정의한 문서는 없다(`preflight-fail-fix-design`도 "수치 경계 없음, S7a에서 명시"라고 적음). 수동 경로의 최고 등급이 `GRADE_B`이고 안 B의 목표가 `GRADE_B`라서 `GRADE_B`는 해제 후보로 볼 근거가 있다. `GRADE_A`는 이름만 근거다. 두 값을 `CAP_RELEASE_GRADES` 상수 한 곳에 두었다. **사용자 확인 필요.** 오늘은 `UNVERIFIED`라서 어느 쪽이든 동작이 같다.
2. **`ROTATE_REVIEW`, `KEEP_CASH`를 EXIT 사유 태그로 분류했다.** G3 결정 4의 문장은 "EXIT → 손실 한도=`EXIT_HARD_STOP`·thesis 훼손=`EXIT_THESIS`, 교체 제안=`ROTATE_REVIEW`, 현금이 나은 경우=`KEEP_CASH`"이고, 카드 행동은 ADD/HOLD/TRIM/EXIT 네 가지라서 이렇게 읽었다. 다르게 정했다면 알려 달라(검증기 `EXIT_TAGS` 한 곳).
3. **`WITHHELD` 행동을 추가했다.** P3 §5-1의 "판단 보류는 두 경우만"을 카드에서 표현하려면 값이 필요하다. plan에는 없는 값이다.
4. **규칙과 "반대"의 정의:** 규칙 방향 `REDUCE`에는 TRIM·EXIT만 "같음", `HOLD`에는 HOLD만 "같음"이다. 그 밖의 조합(예: 정책 hold 종목의 TRIM)도 라벨과 이유를 요구한다. 더 엄격한 해석이다.
5. **레버리지 배수의 출처:** 정책에 구조화된 배수 필드가 없어 `dynamic_gross_leverage_cap.gross_effective_leverage_formula` 문자열(`3*abs(SOXL ...) + 2*abs(MVLL ...) + 2*abs(NBIL ...)`)에서 뽑는다. SOXL 3, MVLL 2. **NBIS는 문자열에 없다(공식에 `NBIL`로 적혀 있음, 오타로 보이나 확인 필요).** NBIS는 `leverage_factor: null`과 결측 코드 `LEVERAGE_FACTOR_NOT_IN_POLICY`로 드러나고 카드에는 "확인 필요"로 표시된다. 파일럿 카드는 NBIS 레버리지를 쓰지 않았다.
6. **timing은 오늘 항상 `NOT_EVALUATED`.** 원본 폴더의 최근 알림 결과 파일은 8/5자(`latest_alert_2026-08-05.json`)라 오래됐다. 실제 `holding_timing_review` 후보의 값은 확인하지 못했고(8/5 파일은 후보 3개의 키만 봤다), 코드는 `evaluate_alerts.py`가 만드는 후보의 `symbol`, `event_type`, `side`, `grade` 이름에 의존한다. 최신 알림 결과가 생기면 1회 확인이 필요하다.
7. **구조화된 숫자만 검증한다.** `numbers` 블록의 11개 값은 fact pack과 일치해야 하지만, 이유·thesis 같은 자유 서술 문장 속 숫자(EMA, 5/20/60일 수익률, 변동성 등)는 검증하지 않는다. 파일럿에서 Cowork가 계산한 값들이며 fact pack에는 없다. P3의 "카드 숫자는 fact pack에 있는 것만"은 구조화 블록에만 강제된다. 기술 지표를 fact pack에 넣을지는 후속 결정이다.
8. **평단 출처:** 손실 한도 기준가는 상태 평단(`system_portfolio_state`)으로 계산한다(알림 엔진과 같음). 브로커 평단과 같은지는 `average_cost_matches_broker`로 싣는다. 카드 `numbers.average_cost_usd`는 브로커 관측값 표시다.
9. **상태 변경 감지:** `--state` 파일의 `state_revision`이 분석 당시와 다르면 `STATE_CHANGED_SINCE_ANALYSIS`로 상한을 유지한다. 상태 파일이 없으면 사유는 아니지만 `state_file_revision_matches_analysis: null`로 남긴다.
10. **`SKILL.md`에 새 명령을 등록하지 않았다.** 배포 게이트 해시에 묶여 있어(P4 §5 대기) 수정하지 않았다. 사용법은 이 보고서에만 있다.
11. **Python 버전:** Python 3.13에서 확인했다. Cowork VM은 3.10인데, 신규 코드는 `from __future__ import annotations`를 쓰고 3.10에 없는 문법을 쓰지 않았지만 VM 실행은 확인하지 못했다.

## 7. 테스트 결과

| 항목 | 결과 |
|---|---|
| 신규 `test_build_holding_fact_pack.py` | 36건 통과 |
| 신규 `test_holding_card.py` | 65건 통과 (거부 7가지 각각, 태그·HOLD 플래그·종목 집합, dashboard 거부, 렌더러, `.gitignore`) |
| 변형 검사(메모리 상에서 코드 12곳을 망가뜨림) | 12곳 모두에서 새 테스트가 실패했다(예: 금지 키 검사 끄기 → 59건 실패, 확신도 허용목록에 `UNVERIFIED` 추가 → 3건 실패, 규칙 방향 검사 끄기 → 5건 실패, 숫자 비교 끄기 → 4건 실패) |
| `.gitignore` 테스트 | 수정 전 7건 실패, 수정 후 통과 |
| 스키마 감사 `validate_schema_contracts.py` | PASS |
| `test_language_contract`(스크립트 ASCII 전용) | 2건 통과 |
| `test_portfolio_status` | 13건 통과 |
| `test_v2_5_beginner_renderer` | 43건 통과 |
| `test_portfolio_decision_dashboard` | 기준선과 같음(FAIL 1, ERROR 187, `INTEGRITY_FAILURE`, worktree 줄바꿈 원시 해시 추정). 신규 dashboard 거부 테스트는 이 스냅샷 경로를 타지 않는 `validate_plan`, `write_decision_plan`을 직접 호출한다 |
| 전체 테스트(서브에이전트) | 2058건, 79초, failures=23, errors=291. 실패 id 314건으로 기준선(1957건, 314건)과 같은 수다. 실질 새 실패 0, 신규 두 모듈은 실패 목록에 없음(기준선 대비 +101건은 신규 테스트). 실행이 저장소에 파일을 만들지 않았다 |

기준선과 id를 대조하면 접두어만 바뀐 1건이 있다: `test_sec_scheduled_shadow`의 `test_05_plan_output_is_sanitized`가 기준선에서는 ERROR(TypeError), 전체 실행에서는 FAIL이다. 같은 테스트가 원래 실패 중이었다. 이 모듈만 두 번 따로 돌리면 두 번 모두 기준선과 같은 5건(01·05·23·35·37)이 FAIL이고, 이 테스트는 신규 파일을 import하지 않는다. ERROR가 FAIL로 바뀐 원인은 확인하지 않았다(환경 의존으로 추정).

dashboard 거부 테스트 내용: 실제 plan(대조군)은 `validate_plan`을 통과하고, 카드는 `DECISION_PLAN_SCHEMA_INVALID`로 거부된다. `plan_id`, `plan_status=CURRENT_APPROVED` 등 plan 필드를 덧붙인 카드도 거부된다. `write_decision_plan`은 카드로 `ContractError`를 내고 파일을 만들지 않는다. 반대로 카드 검증기는 실제 plan 파일(`order_intent_terms`, `proposed_quantity`, `limit_price` 포함)을 거부한다.

## 8. 확인한 경계

- 고정 16개·정책·상태·`SKILL.md`·`portfolio_decision_dashboard.py`·`render_beginner_portfolio_report.py` diff 없음. 저장소 변경은 `.gitignore` +1줄과 신규 파일 7개(이 보고서 포함 8개)다.
- 카드·fact pack에 주문·수량 권한 필드 없음(`order_authority: false`, `quantity_authority: none`, `display_only: true`). 브로커 주문 도구·API 호출 없음.
- 테스트가 저장소 안에 `workspace/outputs/holding-cards/` 산출물을 만들지 않았다(임시 폴더만 사용).
- 계좌번호, 토큰, `.env`는 읽지 않았다.

## 9. 남은 절차

1. 사용자 승인 뒤 Windows 터미널에서 커밋(제안: `feat(cards): add holding card schema, fact pack builder, validator and renderer (I1, K2)`).
2. §3 병합 규칙으로 병합(커밋 ID 기준).
3. Cowork에서 실제 분석 1건으로 카드를 만들어 본다(S7a 완료 기준). 사용자 평가가 "안 씀"이면 S7b로 가지 않고 형식을 먼저 고친다.
4. 확인 필요 1번(등급 허용목록), 5번(NBIS 레버리지), 6번(알림 결과 파일 구조)을 사용자·Judge가 확인한다.
