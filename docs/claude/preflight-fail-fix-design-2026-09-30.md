# 수동 분석 preflight FAIL 수정 설계 (결정 기록)

- 날짜: 2026-09-30
- 등급: K3 설계(읽기 전용). 코드·테스트·정책·상태 파일은 수정하지 않았다.
- 입력: `docs/claude/preflight-fail-diagnosis-2026-09-30.md`
- 기준 코드: `b76d5e7`(I0 병합 `5c02146` 포함)
- 세션: Claude Code, Opus 5.5 / xhigh, worktree `k3-preflight-diagnosis-design-a07b59`(`5db9c32`에서 `b76d5e7`로 fast-forward, 커밋 없음)
- 표기: **확인**은 코드·문서·보고서로 직접 본 것이고, **추론**은 확인하지 못한 것이다.

## 1. 결론과 사용자 결정

1. **`run_manual_portfolio_analysis.py`는 지금 고치지 않는다(NO_CHANGE).** 오늘 FAIL은 로드맵에 이미 잡힌 S1b 경로로 해결한다.
   - **안 A(K2, 관측 추가)** → **빈도 수집** → **안 B(K3, "없음 선언"을 빈 PASS로 인정, 독립 Judge)**
2. 처음 권장했던 **ADD-T**(라이브 부모 시계로 보조 조회 실패 시각을 보정)는 **S8 R6의 선택 항목 ⑨로 대기**시킨다. 사양은 부록 A에 있다.
3. 이유는 세 가지다.
   - **S5 목표 미달.** S5의 목표인 "확신도 상한 해제"에는 낮지 않은 증거 등급이 필요하다. ADD-T는 구조상 PARTIAL → UNVERIFIED여서 이 목표에 닿지 못한다(§4).
   - **로드맵 규칙과 충돌.** P4 §3은 "S8 전까지 고정 파일 16개 수정 금지"다. ADD-T는 고정 파일을 고친다. 안 A와 안 B는 고정되지 않은 브리지만 고친다(§5).
   - **안 B는 오늘 조건 자체를 없앤다.** 모든 조회가 PASS가 되므로 GRADE_B와 `decision_quality_eligible=true`에 닿을 수 있다(추론. 새 cutoff에서 일봉 검증이 통과해야 한다).
4. **사용자 결정 (2026-09-30)**
   1. 위 재권장을 승인했다.
   2. 안 B 착수 기준: **2거래일 이상에 걸쳐 `no_data_declared`를 3회 이상 관측**.
   3. **S5는 먼저 진행한다.** "증거 UNVERIFIED·확신도 상한 유지" 라벨을 붙이고, 확신도 상한 해제는 안 B 뒤로 미룬다.

## 2. 진단 문서 재확인 (b76d5e7)

| 진단 주장 | 진단 줄 | 실제 줄 | 판정 |
|---|---|---|---|
| `_acquisition_complete_cutoff`는 모든 결과에 시각이 있어야 값을 낸다 | rmpa:721 | 721-735 (727행에서 개수가 다르면 None) | 일치 |
| `ACQUISITION_TIMESTAMP_INVALID` | :1744 | 1744-1745 | 일치 |
| `AUTHORITY_REVALIDATION…` 판정에 cutoff 조건이 들어 있다 | :1540 | 1540-1545 (추가 위치 1746-1747) | 일치 |
| `TEMPORAL_EVIDENCE_VIOLATION` | :1805 | 1804-1811 | 일치 |
| 브리지 `_sanitize`가 실패 결과의 시각을 지운다 | bridge:237-241 | **247-249** | I0(`dfb7f7b`)이 `_account_return_code_ok`를 추가하면서 10줄 밀렸다. 내용은 같다 |
| `_failure_timing_evidence` | :812 | 812-846 | 일치 |
| 도입 커밋 | 52fb932 / a5e872a | `git log -S`로 재확인 | 일치 |

보정과 추가 확인:
- **"설계 충돌"보다는 "계약 공백"이다.**
  - 시각 없는 실패를 FAIL로 처리하는 것은 `a5e872a`가 테스트로 의도적으로 고정한 fail-closed 동작이다(`test_scope_missing_capture_or_worker_assertion_cannot_fill_failure_time`, test_manual_portfolio_analysis.py:1161-1167). 결과 dict 안의 `parent_observed_at` 필드로도 시각을 채울 수 없다.
  - 빠진 것은 라이브 CLI 경로의 정당한 실패 시각 출처다. `main()`(2403-2421)은 `parent_capture_artifacts`를 넘기지 않는다. 저장소 안에는 캡처 생성기가 없고 소비자만 있다.
- **진단 §4의 미확인 항목이 해소됐다.** 오늘 실행에는 캡처가 전달되지 않았다. 보고서 5개 모두 `acquisition_scope`가 없다.
- **오늘 5회 모두 같은 패턴이다**(진단은 2회만 직접 확인했다).
  - 계좌 4개는 PASS, `account_open_items`와 `account_realized_pnl_read`는 `KIWOOM_API_RESPONSE_ERROR`였다.
  - 시장 조회는 모두 PASS였고, health HEALTHY, identity/session VERIFIED, cohort MATCHED, 브로커 AVAILABLE, 현금 VERIFIED였다.
- **9/10~9/17 보고서는 같은 두 실패가 있었는데도 `partial_reasons=[]`, PASS/GRADE_B였다.** `ACCOUNT_EVIDENCE_NOT_VERIFIED:` 사유는 `a5e872a`에서 처음 들어왔다. 그래서 시각만 고치면 PARTIAL/UNVERIFIED가 되고, GRADE_B로는 돌아가지 않는다.
- **부수 효과가 있다.** cutoff가 None이면 `session_identity_revalidated=False`(1552-1556)가 되고, 일봉이 NOT_VERIFIED가 된다(1656-1673). 오늘 `finalized_bar_preflight_status=FAIL`과 `TECHNICAL_EVIDENCE_INCOMPLETE`도 같은 원인이다.
- **브리지 간 비대칭이 있다.** 시장 브리지 `sanitize_bridge_response`(kiwoom_runtime_bridge.py:557)는 실패해도 worker의 `retrieved_at`을 유지한다. 계좌 브리지만 지운다.

## 3. 후보 비교 (NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD)

| 후보 | 영향 파일 | K | f0bab 고정 해시 | 판정 |
|---|---|---|---|---|
| NO_CHANGE (rmpa) | 없음 | K0 | 없음 | **채택.** 오늘 FAIL 해결은 안 B가 맡는다 |
| REMOVE: 브리지 247-249의 시각 삭제 되돌리기 | 브리지(고정 아님), test_kiwoom_broker_shadow | K3 | 없음 | 기각. `normalize_snapshot`(broker_shadow:85-86)이 실패 시각을 `broker_snapshot_as_of`에 섞어 I0 스냅샷이 오염된다. 잠긴 원칙(test_kiwoom_broker_shadow:184-209)도 위반한다 |
| SIMPLIFY: cutoff가 시각 없는 실패를 무시 | rmpa(고정), test_manual(고정) | K3 | 2개 | 기각. 잠긴 테스트 4곳 이상(1030, 1166, 1193, 1211)을 약화한다 |
| REUSE: 2단계 캡처 wrapper(고정 아님) | 새 스크립트·테스트 | K3 | 없음 | 예비안. 보고서에 `acquisition_handoff`가 생기고 `observed_at > decision_as_of`가 된다. 그러면 전체 PASS인 날 대시보드 gate(dashboard:1320-1354)가 회귀하고, 진입점도 두 개가 된다. 다만 방향 범위 GRADE_B(rmpa:1114-1119)로 가는 유일한 경로다 |
| REPLACE: 브리지가 in-band `parent_observed_at`을 기록 | 브리지, rmpa(고정), test_manual(고정) | K3 | 1~2개 | 기각. 잠긴 테스트(1161-1167)와 충돌한다 |
| ADD-T: 옵트인 라이브 부모 시계 | rmpa(고정) + 새 테스트 파일 | K3 | rmpa만 바뀜(이미 불일치) | **S8 R6 ⑨로 대기.** 불변식은 지키지만 S5 목표에 미달하고 동결 규칙과 충돌한다 |

## 4. ADD-T vs S1b 안 B

| 기준 | 현재 | ADD-T | 안 B (return_code=20 + `[2000]` → 빈 PASS, 선행: 안 A) |
|---|---|---|---|
| preflight | FAIL (확인) | **PARTIAL** (확인: 판정식 rmpa:1816) | **PASS** 예상 (추론) |
| evidence_grade | UNVERIFIED | **UNVERIFIED** (확인: rmpa:1828) | **GRADE_B 가능** (추론: `finalized_bar_preflight_pass`(1700-1710)도 필요. 9/17은 같은 모양으로 GRADE_B) |
| decision_quality_eligible | false | **false** (확인: sidecar:296-299) | **true 가능** (추론) |
| 부수 효과 | 일봉 NOT_VERIFIED | 일봉 검증이 다시 작동 | 같음 + 미체결 `VERIFIED_NONE`(dashboard:984), `scope_complete=true`, I0 제안 `verified_scope=FULL` |
| 수정 파일 | — | rmpa(**고정**) + 새 테스트 | A: 브리지, `broker_visibility_audit.py`, 그 스키마. B: 브리지. **모두 고정 아님.** 배포 `required_code_paths`(rmpa:2226-2232)에도 없다 |
| K | — | K3 | A: K2, B: K3 (`VERIFIED_NONE`은 주문 의도 차단 해제 쪽에 있다) |
| 위험 | 매일 FAIL이 나서 신호 가치가 없다 | ① 새 시각 출처 ② 로드맵 예외 필요 ③ S5 목표 미달 | ① 코드 20은 스펙 오류표에 없어 다른 오류와 겹칠 수 있다 ② 한국어 메시지 접두 `[2000]`에 의존한다 ③ "없음" 선언의 시각 의미가 약하다 → 좁은 조건과 Judge로 관리 |
| 테스트 규모 | — | 새 파일 1개, 약 13건 | A: 약 4~6건 + 스키마. B: 약 10~15건. `test_return_code_twenty_is_still_error`(test_k2_bridge_evidence_integrity.py:278)는 그대로 통과해야 한다 |

두 안 모두 ET 자정을 넘기는 실행은 `ACQUISITION_SESSION_ROLLOVER`로 FAIL이 된다. 이는 올바른 동작이다. 오늘 실행은 22:34~23:36 ET였다.

## 5. S5 카드 파일럿과 사후 채점의 등급 요건

| 대상 | 요건 | 근거 |
|---|---|---|
| S5 카드 작성 | GRADE_B는 필요 없다. 판단은 항상 낸다. 판단 보류는 브로커 UNAVAILABLE과 identity 미검증 두 경우만 허용한다 | P3 §5-1, P4 §4 S2 |
| S5 목표(확신도 상한 해제) | 낮지 않은 증거 등급과 조정된 상태가 필요하다. 수동 경로의 최고 등급이 GRADE_B이므로 사실상 GRADE_B가 필요하다 | P3 §5-1 "증거 등급이 낮거나 상태가 미조정이면 확신도는 '낮음'까지만", P4 §4 S5 "확신도 상한이 풀리고". "낮은 등급"의 수치 경계는 문서에 없다(추론) |
| S7a 카드 검증기 | 확신도 상한(낮은 증거 등급, 미조정 상태)을 검증한다 | P3 §5-4 |
| S7b 사후 채점 | GRADE_B는 필수가 아니다. 원장에 `evidence_grade`를 기록하기만 한다. `evaluate_forward_outcomes`(sidecar:486-536)는 적격성으로 거르지 않는다. 다만 UNVERIFIED는 판단 품질 적격 집계(sidecar:975-976)에서 빠진다 | P3 §6-2, 코드 확인 |

## 6. acceptance 6~9단계(S8 R6~R9) 보류 결정과의 관계

- **ADD-T는 규칙과 정면 충돌한다.**
  - P4 §3 공통 규칙은 "S8 전까지 거버넌스 확장과 고정 파일 16개 수정 금지"다(G0 승인). P3 §8-3도 "run_manual과 고정 파일은 수정하지 않는다"고 정했다.
  - 지금 하려면 이 규칙에 예외를 두는 사용자 결정이 필요하다.
  - 미루면 S8 R6에 ⑨로 합류하는 것이 자연스럽다. R6 ⑧이 이미 rmpa를 고치고, R8 Judge 한 번으로 함께 본다.
  - 반대로 지금 하면 R6 ②③(보호 기능 모듈 분리, rmpa 고정 해제)에서 코드 위치가 바뀌어 재작업 위험이 있다.
- **안 A와 안 B는 규칙 밖이다**(고정되지 않은 파일).
  - 로드맵 §5 대기표의 순서("안 A: G2 뒤, 안 B: 빈도 수집 뒤")를 그대로 따른다. G2는 9/30에 통과했다.
  - S8과의 접점은 R8의 "I0 테스트 재실행"에서 바뀐 브리지 동작을 함께 확인하는 것뿐이다.
- **공통:** CI 알려진 실패 17건은 변화가 없다. 예약 실행은 별도 clone(`runtime/stock-strategy-scheduled` @ `41f7b3f`)이라 즉시 영향이 없다.

## 7. 실행 순서

1. **안 A — 관측 추가 (K2).** 새 Claude Code 세션(Sonnet · high, worktree `s1b-plan-a`)에서 한다. 설계는 `open-orders-diagnosis-2026-09-30.md` §5-1이다.
   - 오류 결과에 정제된 `provider_return_code`(정수만)와 `no_data_declared`(return_code==20 **이고** 메시지가 `[2000]`로 시작할 때만 true)를 붙인다.
   - 원문 메시지는 저장하지 않는다. `bridge_status`와 모든 게이트는 바꾸지 않는다.
   - **Builder가 먼저 확인할 것:** rmpa는 브리지 `_sanitize`를 import해 `open_order_evidence`를 만든다(rmpa:33, 336). 그래서 새 필드가 수동 분석 보고서에도 나타난다.
     - `broker_observed_state`는 `additionalProperties: true`임을 확인했다. 하위 `open_order_evidence`의 제약은 확인하지 못했다.
     - rmpa나 고정 파일을 고쳐야 하게 되면 멈춘다.
2. **빈도 수집.** 사용자가 평소대로 수동 분석을 돌린다. 기준은 2거래일 이상, `no_data_declared` 3회 이상이다.
3. **안 B — 빈 PASS 인정 (K3).** 같은 문서 §5-2를 개정한 뒤 독립 Judge를 거친다. 개정 때 반영할 점은 두 가지다.
   - `_read_pages`의 미체결 연속조회 엄격 검사(bridge:145-167)가 "없음" 응답에서 `break`하면 `complete=False`, 즉 PARTIAL로 남는다. 따라서 "없음 선언"은 연속조회 검사 **앞에서** 종결 처리한다.
   - 대상은 미체결과 실현손익 두 연산만이다.
4. **S5.** 안 B를 기다리지 않고 먼저 진행한다. 카드에 "증거 UNVERIFIED·확신도 상한 유지" 라벨을 붙인다(사용자 결정 3). 확신도 상한 해제는 안 B 병합 뒤 카드에서 본다.
5. **ADD-T.** S8 R6 ⑨ 대기. 착수 조건은 안 B 이후에도 보조 조회 오류로 FAIL이 반복되는 경우다.
6. **미수행.** P4 로드맵 §5 대기표와 §9 기록 갱신은 이 문서를 커밋한 뒤 Cowork에서 한 줄로 남긴다.

## 8. 남는 위험 / 확인 못 한 것

- 안 B의 GRADE_B는 추론이다. 새 cutoff에서 권한 재검증과 9/28 일봉 검증이 통과하는지는 9/17 이후 라이브로 확인된 적이 없다. 안 B 병합 뒤 라이브 실행 1회로 확정한다.
- 코드 20의 다른 의미, "없음" 선언의 시각 의미, 미체결이 실제로 있을 때의 실응답은 확인하지 못했다(S1b §3-4). 안 A 관측과 Judge로 다룬다.
- "낮은 증거 등급"의 경계는 문서에 수치로 없다. S7a 카드 검증기 설계 때 명시해야 한다.
- 안 B 이후에도 보조 조회에 다른 오류가 한 건이라도 나면 FAIL이다. fail-closed이므로 허용한다.
- 52fb932가 실패 시각을 지운 의도는 커밋 메시지로 확인하지 못했다(주석만 있음).
- 오늘 실현손익 실패 결과의 `retrieved_at`이 None이라는 것은 같은 정제 경로에서 추론한 것이다. 보고서에는 상태만 남는다.

## 부록 A. ADD-T 사양 (S8 R6 ⑨ 후보)

- **매개변수:** `run_manual_preflight(..., live_parent_failure_clock=None)`.
  - 기본값이면 모든 기존 호출자의 동작이 같다.
  - `main()`만 넘기며, `--observed-at`과 `--decision-as-of`가 모두 없을 때만 넘긴다.
- **가드:** 시계와 함께 아래 중 하나라도 주어지면 리더를 호출하기 전에 `ValueError`를 낸다.
  - `parent_capture_artifacts is not None`(빈 리스트 포함)
  - `direction_only`
  - `account_operations`
  - `market_operations`
- **괄호 측정:** 계좌 리더 호출 직전에 t0, 직후에 t1을 읽는다. 아래를 모두 만족할 때만 채운다.
  - t0와 t1이 timezone-aware이다.
  - `initial_observation ≤ t0 ≤ t1`이다.
  - 모든 PASS/PARTIAL 계좌 시각이 [t0, t1] 안에 있다. 이 조건이 저장된 성공 결과의 재생을 거른다.

  시계가 예외를 내거나 값이 이상하면 채우지 않는다.
- **채우는 대상:** 아래를 모두 만족하는 결과만 채운다. 값은 t1이고, 분리된 timing view에만 넣는다.
  - `result.operation == request.operation`
  - 보조 조회 4개(deposit_detail, open_items, fills, realized_pnl) 중 하나
  - 상태가 `KIWOOM_API_RESPONSE_ERROR`
  - `retrieved_at is None`

  `account_results`, `broker_state.as_of`, `open_order_evidence`는 바꾸지 않는다.
- **기록:** `manual_analysis_view.live_parent_failure_timing` = `{operation, ticker, request_sha256, result_sha256, parent_started_at, parent_observed_at, timestamp_role: FAILURE_OBSERVATION_ONLY, timing_source: LIVE_PARENT_READER_RETURN}`
- **불변식:**
  - fail closed다.
  - 시각 없는 실패는 성공 증거를 통과시키지 못한다. partial 사유는 원본 결과로 계산하므로 PASS나 GRADE_B에 도달할 수 없다.
  - 재생 경로에서는 쓸 수 없다(가드와 괄호 검사).
  - 계좌 값이 드러나지 않는다.
  - 검증 함수는 바꾸지 않는다. t1은 실제 실패 이후 시각이므로 cutoff를 앞당기지 않는다.
- **테스트(새 파일, 고정 테스트 모듈은 fixture만 import).** `ManualPortfolioAnalysisTest`는 import하지 않는다. 115건이 다시 실행되기 때문이다.
  - 결과 판정: 오늘 조건 → PARTIAL, 시계 없음 → FAIL, 기본값일 때 기존과 동등, ROLLOVER
  - 가드와 범위: 가드 4종, 핵심·시장 조회 제외, 상태 한정
  - 입력 방어: 보정 금지, 괄호 위반, in-band 필드 무시
  - 경계: 승격 불가, `main()` 연결, 누출 없음

## 부록 B. 확인에 쓴 명령 (읽기 전용)

- `git --no-optional-locks log -S "safe.update(runtime_commit=None, retrieved_at=None" b76d5e7 -- …/kiwoom_account_readonly_bridge.py` → `52fb932`
- `git --no-optional-locks log -S "ACCOUNT_EVIDENCE_NOT_VERIFIED:" b76d5e7 -- …/run_manual_portfolio_analysis.py` → `a5e872a`
- 9/10~9/30 수동 분석 보고서에서 상태 필드만 추출했다(보유·현금 값은 출력하지 않음).
- f0bab manifest의 `implementation_hashes` 목록: 브리지 파일이 없음을 확인했다.
