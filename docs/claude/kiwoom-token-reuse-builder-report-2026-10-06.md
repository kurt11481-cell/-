---
id: kiwoom-token-reuse-builder-report-2026-10-06
type: builder-report
status: current
as_of: 2026-10-06
summary: 키움 토큰 재사용(A)과 세션당 1회 자동 복구(B) K3 Builder 결과. 브리지가 정책 별칭의 kiwoomcli 파일 토큰을 재사용하고, 인증 실패 시 세션당 1번만 복구·재전송한다. 현재 키움 acceptance는 무효가 되며, 재고정을 열기 위한 pin scope 수정(predecessor 45cf, 허용 drift 2개 파일)을 이번 변경에 포함했다(사용자 승인 2026-10-06).
consumers: [Cowork 사전 확인 → Judge 지시문, acceptance 재고정 K3 단계, references/portfolio-exposure-review.md Routine 서두(실측 확인 뒤), 개발 관제판]
---

# 키움 토큰 재사용 K3 Builder 보고 (2026-10-06, Claude Code Builder)

**허용 drift는 넓어지지 않았다:** 45cf manifest가 고정한 27개 파일 중 45cf 이후 바뀐 것은 브리지와 pin scope 자신뿐이고(정규화 해시 비교, 11-1절), 허용 목록은 이 두 개로 **교체**되어 이전 6개(그중 4개는 45cf가 고정하지도 않음)보다 좁으며, predecessor가 45cf가 아니면 `allowed_drift_for`가 빈 목록을 돌려준다(test_21·22, 변이 5종 확인).

근거: `kiwoom-token-reuse-review-2026-10-06.md`, 지시문 `kiwoom-token-reuse-builder-prompt-2026-10-06.md` 2절. 사용자 승인 2026-10-06 "A + 1회 자동 복구로 진행 승인", 이어서 같은 날 "pin scope 수정(가) 승인함. 교체 방식(허용 목록을 두 파일로 교체)도 승인함"(이 대화에서 사용자가 직접 입력). 커밋·푸시하지 않았다. 키움 실제 접속, kiwoomcli 실행, `.env`·토큰·키링 읽기, materialize·activate 실행은 하지 않았다.

## 0. 맨 위 — acceptance가 무효인 동안 막히는 것과 사용자 결정

**운영 실행 경로에서 막히는 것: 없음.** acceptance 고정 해시를 다시 계산하는 코드는 `validate_kiwoom_session_aware_acceptance.validate_acceptance`뿐이고, 이것을 부르는 곳은 materialize 스크립트와 후보 검증기(`validate_kiwoom_session_aware_acceptance_candidate.py`)뿐이다(grep 확인). 수동 분석, 대조 propose, broker shadow, provider preflight, 시장 스냅샷, 현황판은 acceptance 유효성을 읽지 않는다. 정책은 그대로 `KIWOOM_PRIMARY_GUARDED_SCOPED`로 남아 있어 무효 상태가 화면에 드러나지 않는다(조용한 drift).

막히거나 바뀌는 것:

1. **재고정 막힘 → 사용자 결정: pin scope 수정 포함(가), 사용자 승인 2026-10-06. 반영함(11절).** 수정 전에는 pin scope(`assets/kiwoom-acceptance-pin-scope.json`)의 `allowed_drift_predecessor_sha256`이 `f0bab710…`(이전 acceptance)이고 현재 활성 acceptance는 `45cf1888…`라, `allowed_drift_for`(`validate_kiwoom_session_aware_acceptance_candidate.py:372-377`)가 빈 목록을 돌려주어 materialize가 `current active Acceptance invalid beyond allowed drift: ['implementation hash mismatch: manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py']`로 거부했다(`materialize_…:156`, `:181-185`). 이제 predecessor는 `45cf1888…`, 허용 목록은 `kiwoom_runtime_bridge.py`와 pin scope 자신 두 개뿐이다. pin scope도 고정 대상이므로 이 수정 자체가 drift 하나를 더한다(그래서 자기 자신을 목록에 넣음). 이번 변경 전체에서 바뀐 고정 파일은 **브리지와 pin scope 두 개**이고, 나머지 25개(계좌 브리지 포함)는 그대로다.
2. **테스트·CI 실패.** 전체 스위트 비교는 6-4절(브리지 변경)과 11-3절(pin scope 변경). pin scope 수정으로 materialize 테스트의 drift 오류 14건은 풀렸다. 남는 새 실패는 shadow semantic fingerprint 테스트(정책 파일 바이트 변경, 3번)이고, worktree에서는 원본 산출물이 없어 test_05·test_12가 `source artifact missing`으로 실패한다(환경, 11-2절).
3. **shadow semantic fingerprint가 바뀐다.** `workspace/policies/kiwoom-readonly-policy.json`은 `shadow_acceptance.SEMANTIC_DEFAULTS`(`shadow_acceptance.py:70`)에 들어 있다. 별칭 키 추가로 fingerprint가 바뀌어 `test_v2_6_7…test_provider_authority_change_starts_zero_count_cohort`가 실패한다. 다음 `record_integrated_shadow_attempt.py` 실행은 보관 기록 없이 새 0 cohort를 시작한다(`shadow_acceptance.py:577-580`). 지금 카운터는 모두 0이라 잃는 기록은 없다(worktree 사본 기준; 원본 폴더 값은 확인 필요). 재고정 활성화 때 `migrate_integrated_shadow_cohort.py`를 한 번 실행해야 하며, 상태 쓰기라 사용자 승인이 필요하다.
4. 재고정 뒤에는 `scheduled_input_gate.py`의 배포 출처 검사가 `CURRENT_PROVIDER_SCOPE_HASH_MISMATCH`·`CURRENT_SEMANTIC_COHORT_MISMATCH`를 낼 수 있다. 예약 런타임 clone 경로에서만 해당하며 그 경로는 문서상 보류 중이다(코드로 확인 못 함, 확인 필요).

## 1. 기준 확인

- HEAD `782d61b` = 기준 `e8147225` + 지시문 1절 2번의 문서 커밋(문서 2개, +133줄만). 지시문 절차대로라 차이로 보지 않았다.
- blob 4개 모두 일치: `kiwoom_runtime_bridge.py` `28837ecb…`, `kiwoom_account_readonly_bridge.py` `80634069…`, `kiwoom-readonly-policy.json` `55bf7f34…`, `kiwoom-acceptance-pin-scope.json` `1a7c8ca2…`.
- 외부 런타임 HEAD `69642586…` = 정책 `official_runtime_commit`(`.git/HEAD`·ref 파일만 읽음, 작업 트리 수정 여부는 확인 못 함).

## 2. 바뀐 파일·줄 수

| 파일 | 변경 | 비고 |
|---|---|---|
| `manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py` | +116 −5 | pin 대상(K3). CRLF 유지 |
| `workspace/policies/kiwoom-readonly-policy.json` | +1 | 키 하나만 추가: `"token_profile_alias": "실전계좌"`. 줄바꿈 변환 없이 수정(worktree 파일은 CRLF, 원본 폴더는 CRLF·LF 혼재, Judge 확인; 해시는 정규화 방식이라 영향 없음) |
| `manage-us-stock-strategy/references/portfolio-exposure-review.md` | +6 | Routine 서두 토큰 문단 끝에 조건부 문장 추가(K0). 기존 문장 무변경 |
| `manage-us-stock-strategy/tests/test_kiwoom_token_reuse.py` | 새 파일 374줄 | CRLF(옆 테스트 파일과 같게) |
| `manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json` | +2 −6 | pin 대상(K3, 11절). 두 필드만: predecessor → `45cf…`, 허용 목록 6개 → 2개 교체. CRLF 유지 |
| `manage-us-stock-strategy/tests/test_materialize_kiwoom_session_aware_acceptance_candidate.py` | +40 | `PinScopeAllowanceTest`(test_21·22) 추가, import 1줄. 기존 테스트 무변경. CRLF 유지 |
| `docs/claude/kiwoom-token-reuse-builder-report-2026-10-06.md` | 새 파일 | 이 보고 |

`kiwoom_account_readonly_bridge.py`(pin 대상)와 `kiwoom_candidate_discovery_bridge.py`는 바꾸지 않았다. 주문 경로(`BLOCKED_TERMS`, `RUNTIME_APIS`, `blocked_api_target`, `ALLOWED_OPERATIONS`)는 그대로다.

## 3. 사실 확인 (1단계, 코드 읽기)

### 3-1. `_runtime_session` 호출처와 각자 읽는 정책

| 호출처 | 위치 | 부모가 넘기는 정책 |
|---|---|---|
| 시장 데이터 워커 `kiwoom_runtime_bridge.external_worker` | 변경 전 461행 | `kiwoom-rate-limit-policy.json`(부모 `invoke_bridge`/`invoke_bridge_batch`의 `policy`) |
| 계좌 워커 `kiwoom_account_readonly_bridge.external_worker` | 274행 | 같은 rate-limit 정책(`invoke_account_bridge_batch`) |
| 후보 발굴 워커 `kiwoom_candidate_discovery_bridge.external_worker` | 190행 | `kiwoom-candidate-discovery-readonly-policy.json`(봉투로 전달) + rate-limit 정책(파이썬 경로) |

세 워커 모두 외부 런타임 파이썬으로 `cwd=runtime`에서 실행되고, 지금까지 `kiwoom-readonly-policy.json`은 워커에 전달되지 않았다(부모의 `--readonly-policy`는 런타임 경로·커밋 검사에만 쓰임).

### 3-2. 외부 런타임 동작 (commit `69642586`)

- `runtime.get_auth(mode, *, profile, token_store_kind)`: profile을 주면 `get_profile(alias)`로 별칭을 찾고, mode를 함께 주었는데 별칭의 mode와 다르면 `ValueError`(runtime.py:44-50). 자격 공급자는 `default_secret_provider(profile=alias)`.
- `secrets.default_secret_provider(profile=…)`: 별칭 키링(`ProfileKeyringSecretProvider`)만 쓰고 env 공급자는 넣지 않는다(secrets.py:200-207). 키링을 못 쓰면 `None`.
- `auth.get_access_token`: `_load_valid_token`이 파일 토큰을 읽어 유효하면 재사용, 아니면 `refresh_access_token`(auth.py:108-112). `_load_valid_token`은 지문 없음·자격 지문 불일치·만료 10분 전(`refresh_buffer_seconds=600`)이면 토큰을 지운다(auth.py:243-261). **주의: 자격 증명이 `None`이면 지문 비교 없이 유효한 파일 토큰을 그대로 돌려준다**(auth.py:253-257) — 그래서 브리지에서 자격 존재를 따로 확인한다(4절).
- `refresh_access_token`: 새 토큰을 받아 `token_store.save`(auth.py:114-159). `recover_from_auth_failure` = `clear_token` + `refresh_access_token`(auth.py:167-169).
- `token_store.FileTokenStore`: 별칭 토큰 경로 `cache_dir()/profiles/profile-<sha256(alias)[:16]>-token.json`, 임시 파일에 쓰고 `replace`로 원자적 교체(token_store.py:143-161, 174-178).
- `client.KiwoomClient.request`: HTTP 401이면 `retry_on_auth_failure`일 때만 복구·재시도, 아니면 `AuthenticationError`(상태 코드 속성 없음)를 던진다(client.py:60-71). `return_code`가 8005·8031·8103(정수화)일 때도 같은 자동 복구(client.py:83-93, `errors.AUTH_RETRY_RETURN_CODES`). 실제 응답 `return_code 3` + `return_msg` 안 `[8005:`는 걸리지 않는다(검토 문서 2절과 일치).
- **추가 발견: `fetch_page`는 `retry_on_auth_failure`를 넘기지 않아 기본값 True로 자체 복구를 한다**(client.py:102-129). 브리지의 `_request`는 False를 넘기지만 `_fetch_page`(daily_chart), 계좌 브리지, 발굴 브리지 REST 경로는 모두 `fetch_page`라 런타임이 스스로 토큰을 다시 받을 수 있었다(요청마다, 횟수 제한 없음). 메모리 저장소일 때는 kiwoomcli 토큰만 무효화할 수 있었고(서버 규칙은 확인 필요), 파일 저장소로 바꾸면 공유 파일을 다시 쓰게 된다 → 이번 변경에서 같은 1회 예산에 묶었다(5절).

### 3-3. 계좌 별칭

- 지시문이 가리킨 근거(`s7-builder-report-2026-10-01.md` 989행)에는 "실전계좌" 문자열이 없다(파일 전체에도 없음). 근거 표기는 틀렸다.
- 외부 런타임의 읽기 전용 `kiwoom.core.profiles.load_profiles()`(settings.json의 별칭→mode만 읽음, 키·토큰 없음)로 확인: **"실전계좌" 존재, mode `real`, 등록 별칭 1개.** 출력한 것은 이 세 값뿐이다.

### 3-4. 인증 실패 분류와 회로 (변경 전 실제 동작)

- `_exception_failure`: 예외의 `status_code`가 429면 `HTTP_429`, 401·403이면 `AUTHENTICATION_FAILURE`, `BridgeError`면 그 `failure_type`, 나머지는 `EMPTY_RESPONSE`.
- 회로: rate-limit 정책 `immediate_open_failure_types = [HTTP_429, AUTHENTICATION_FAILURE]`이면 요청 재시도 없이 올리고, 시장 워커 배치는 `BridgeError`가 아닌 예외가 이 두 유형일 때만 나머지를 `KIWOOM_CIRCUIT_OPEN`으로 채운다. 계좌 워커에는 배치 회로가 없다(요청마다 실패 기록 후 다음 요청 진행).
- **지시문과 다른 점:** 지시문은 "재시도도 실패하면 지금 동작 그대로 AUTHENTICATION_FAILURE + 회로 차단"이라 했지만, 변경 전 실제로는
  - `return_code 3` + `[8005:` → 시장: `KIWOOM_API_UNAVAILABLE`/`EMPTY_RESPONSE`(재시도 가능, 회로 안 열림), 계좌: `KIWOOM_API_RESPONSE_ERROR`/`API_RESPONSE_ERROR`(provider_return_code 3).
  - HTTP 401(`retry_on_auth_failure=False`) → 런타임 `AuthenticationError`에 `status_code`가 없어 `EMPTY_RESPONSE`.
  - `AUTHENTICATION_FAILURE`가 되던 것은 HTTP 403(`HTTPRequestError`)과 주문 차단 `BridgeError`뿐이었다.
  
  지시문 T4가 요구한 결과(AUTHENTICATION_FAILURE + 회로 차단)를 따랐다. 판정 함수가 잡는 인증 실패는 이제 더 엄격한 쪽(회로 차단)으로 분류된다 — Judge 확인 대상.

## 4. 변경 A — 토큰 공유

- 정책: `workspace/policies/kiwoom-readonly-policy.json`에 `"token_profile_alias": "실전계좌"` 한 키만 추가. 이 파일의 키 집합이나 해시를 검사하는 코드·테스트는 없다(acceptance 해시·pin scope·배포 출처 정책 목록에 없음). 유일한 영향은 shadow semantic fingerprint(0절 3번).
- `_runtime_session`(kiwoom_runtime_bridge.py:447-):
  1. `_token_profile_alias()`(355행)가 정책을 읽어 별칭을 돌려준다. 파일 없음·JSON 오류·객체 아님·키 없음·문자열 아님·빈 값/공백 → `BridgeError("KIWOOM_API_UNAVAILABLE", "AUTHENTICATION_FAILURE")`로 fail-closed. `get_auth`는 부르지 않는다.
  2. `get_auth(mode="real", profile=alias, token_store_kind="file")`. mode를 같이 넘겨 별칭이 real이 아니면 런타임이 거부하고, 브리지도 `auth.mode == "real"`을 다시 확인한다.
  3. `auth.status().has_credentials is True`가 아니면 fail-closed(별칭 키링 자격 없음). 3-2의 "자격 없으면 파일 토큰을 그냥 재사용" 경로를 막는다. `get_auth`·`status` 예외(별칭 미등록 등)도 같은 fail-closed.
  4. `auth.get_access_token()`으로 토큰 확보: 유효한 파일 토큰 재사용, 없거나 만료 10분 전일 때만 발급해 같은 파일에 저장. `refresh_access_token()`은 직접 부르지 않는다.
- env 자격으로 넘어가는 대체 경로 없음: profile을 주면 런타임이 env 공급자를 쓰지 않는다. `_load_env_without_echo(runtime/.env)` 호출은 그대로 두었다(기본 URL 등 다른 env용; 선택·자격에는 영향 없음 — `mode`·`profile`을 명시해 `KIWOOM_MODE`/`KIWOOM_PROFILE`도 무시됨).
- **전달 방식 선택: "같은 정책에서 읽기"(워커가 `_runtime_session` 안에서 읽음).** 이유: 세 호출처가 모두 `kiwoom_runtime_bridge._runtime_session` 한 함수를 쓰므로, 여기서 읽으면 호출처·부모 함수·CLI 인자를 하나도 바꾸지 않고 모두 같은 별칭을 쓴다. 인자로 넘기려면 `invoke_bridge`·`invoke_bridge_batch`·`invoke_account_bridge_batch`(pin 대상)·발굴 브리지와 그 부모들(reconcile_broker_state 등 pin 대상)이 readonly 정책을 따로 읽어 넘겨야 해서 고정 파일 변경이 늘어난다. 경로는 저장소 관례(`REPO_ROOT = Path(__file__).resolve().parents[2]`)를 따랐다.
  - 결과로 생기는 차이: 부모 CLI의 `--readonly-policy`로 다른 정책 파일을 주어도 별칭은 항상 저장소 기본 정책에서 읽는다(확인 필요 목록에 적음).

## 5. 변경 B — 세션당 1회 자동 복구

- 판정 함수 하나: `_auth_failure(outcome, runtime_auth_errors)`(367행). 참: HTTP 401(`status_code == 401`), 런타임 `AuthenticationError`(401 재시도 끔일 때 런타임이 던지는 예외; 전달받은 클래스로만 판별), 이미 복구에 실패한 `KiwoomAuthFailure`, 본문 `return_code` ∈ {8005, 8031, 8103}(정수·숫자 문자열, bool 제외), `return_code` 3이면서 `return_msg`에 `[8005:`·`[8031:`·`[8103:` 중 하나. 결과는 참/거짓뿐이고 메시지·토큰은 어디에도 옮기지 않는다.
- `_SingleRecoveryAuth`(386행): 런타임 auth를 감싼 얇은 겉면. `recover_from_auth_failure()`는 세션 플래그 `recovery_attempted`로 **한 번만** 진짜 복구(공유 파일 토큰 삭제 → 발급 → 같은 파일 저장)를 하고, 두 번째부터는 `KiwoomAuthFailure`. 복구가 예외로 실패해도 `KiwoomAuthFailure`. 복구 뒤 `pacer()`를 불러 재전송 전 요청 간격을 지킨다. 런타임 client를 이 겉면으로 만들었기 때문에 **`fetch_page`의 런타임 자체 복구(3-2 추가 발견)도 같은 1회 예산을 쓴다.**
- `_AuthRecoveringClient`(410행): `request`·`fetch_page` 겉면. 응답이나 예외가 인증 실패면 복구 1회 → 같은 요청을 1번만 다시 보낸다. 다시 보낸 결과도 인증 실패면 `KiwoomAuthFailure`. 성공 응답은 그대로 돌려주어 호출자의 기존 `return_code`·스키마 검증을 그대로 거친다(복구가 실패를 PASS로 바꾸지 않음). HTTP 429는 판정에 걸리지 않아 복구 없이 기존대로 `HTTP_429` + 회로 차단.
- `KiwoomAuthFailure`(65행, 메시지 없음)는 `_exception_failure`에서 `AUTHENTICATION_FAILURE`(169행)로 분류된다 → 시장 워커는 `KIWOOM_API_UNAVAILABLE`/`AUTHENTICATION_FAILURE` + 나머지 `KIWOOM_CIRCUIT_OPEN`, 계좌 워커는 해당 요청 `KIWOOM_API_UNAVAILABLE`/`AUTHENTICATION_FAILURE`(배치 회로 없음은 기존과 같음, 남은 계좌 요청은 1번씩 보내지고 복구 없이 실패), 발굴 워커 REST도 같은 분류.
- `auth_recovery_attempted` 출력 필드: **넣지 않았다.** 부모의 `sanitize_bridge_response`(시장)와 `_sanitize`(계좌)가 화이트리스트라 전달하려면 두 sanitize와 증거 스키마까지 바꿔야 하고, 계좌 브리지는 pin 대상이라 변경 범위가 커진다. 세션 객체의 `session["auth"].recovery_attempted`에는 남는다(출력 안 됨).

### 5-1. 동작 변화 목록 (Judge 확인용)

1. 인증 실패(3-4의 응답들) 분류: `EMPTY_RESPONSE`/`API_RESPONSE_ERROR` → 복구 1회 뒤에도 실패하면 `AUTHENTICATION_FAILURE`(시장 배치는 회로 차단). 더 엄격한 방향.
2. 계좌 쪽 이 경우의 `provider_return_code`는 3 → `None`, `broker_visibility_audit`의 표시 분류는 `API_RESPONSE_ERROR` → `PARTIAL_PROVIDER_SUPPORT`(상태는 둘 다 `UNKNOWN`, 표시만 바뀜).
3. `oauth_health`의 `authenticated`: 전에는 "새 토큰 발급 성공"(서버 왕복), 이제는 "유효 기간 안의 토큰 확보(재사용 또는 발급)". 재사용하면 서버 왕복이 없어 서버가 그 토큰을 받아 줄지는 증명하지 않는다. 서버 수용은 첫 데이터 요청에서 검증되고, 거부되면 1회 복구한다. `kiwoom_provider_preflight`의 `AUTHENTICATION_FAILURE`/`AUTHENTICATED` 의미가 이만큼 약해진다.
4. 단일 요청 모드 `invoke_bridge`는 비인증 실패 때 워커를 정책 `maximum_attempts`(2)까지 다시 띄운다. 워커마다 새 세션·새 예산이라, 인증 실패 → 복구 성공 → 비인증 실패 → 워커 재실행 → 또 인증 실패가 겹치면 부모 호출 1번에 복구가 최대 2번 될 수 있다. 인증 실패 자체는 부모가 즉시 돌려주므로 재실행하지 않는다. "워커 세션 1회당 최대 1번"은 지킨다.
5. 발굴 브리지의 WebSocket 경로(`_fetch_websocket`의 `get_ws_client()`)는 바꾸지 않았다. 이 경로는 원래 기본 선택(env `KIWOOM_PROFILE`/현재 별칭)과 파일 토큰을 쓴다.

## 6. 테스트

### 6-1. 새 테스트 `manage-us-stock-strategy/tests/test_kiwoom_token_reuse.py` (15개, 네트워크 없음)

가짜 `kiwoom`·`kiwoom.core.errors` 모듈(런타임 commit `69642586`의 `get_access_token` 재사용·10분 버퍼, `recover_from_auth_failure`, `fetch_page` 자체 복구를 흉내), 임시 정책 파일, `_runtime_commit`·env 로드·시계 패치.

| ID | 테스트 | 결과 |
|---|---|---|
| T1 | 유효한 파일 토큰 → 발급 0회, `get_auth(mode="real", profile=별칭, token_store_kind="file")` | PASS |
| T2 | 토큰 없음/만료 임박(300초) → 발급 1회, 같은 저장소에 저장, 다음 요청은 재사용 | PASS |
| T3 | `return_code 3` + `[8005:` → 복구 1회 → 재시도 성공 → PASS, 재전송 전 pacer 대기 1번(0.25초) 확인. 계좌 페이지도 같음. 복구 뒤 응답이 `return_code 20`/없음이면 기존대로 실패 | PASS |
| T4 | 복구 뒤에도 인증 실패 → `AUTHENTICATION_FAILURE`, 남은 요청 `KIWOOM_CIRCUIT_OPEN`, 복구 정확히 1회 | PASS |
| T5 | 같은 세션 두 번째 인증 실패 → 복구 안 함. 런타임 `fetch_page` 자체 복구(HTTP 401, 8005)도 같은 1회 예산 | PASS |
| T6 | 별칭 키 없음/빈 값/공백/숫자/null/정책이 목록/JSON 오류/파일 없음 → `get_auth` 호출 0회, fail-closed. 자격 없음(유효한 캐시 토큰이 있어도) → fail-closed·발급 0회. 별칭 미등록·demo 별칭·demo auth → fail-closed | PASS |
| T7 | 시장·계좌 `main()` 실행: 결과 JSON·stdout·stderr에 가짜 토큰 문자열과 `8005:` 메시지 없음(토큰을 담은 예외 메시지·return_msg를 일부러 주입) | PASS |
| T8 | HTTP 429 → 복구 0회, 발급 0회, `HTTP_429` + 회로 차단 | PASS |
| — | 판정 함수 표 검사, 세 호출처가 같은 `_runtime_session` 객체를 씀 | PASS |

검증력 점검(작업 폴더 밖 scratch 사본에서): 새 코드를 11가지로 일부러 망가뜨려 각 경우 최소 1개 테스트가 실패함을 확인했다 — 복구 예산 제거, 무조건 `refresh_access_token`, 메모리 저장소, 자격 확인 제거, mode 확인 제거, 재전송 pacer 제거, `[8005:` 메시지 판정 제거, 재전송 실패 통과, 429 복구, `KiwoomAuthFailure` 미분류, 별칭 없을 때 통과. 11/11 실패 확인. 변경 전 코드에는 구조 검사 1개 외 전부 실패.

### 6-2. 기존 대상 테스트 (변경 뒤, worktree)

| 파일 | 결과 |
|---|---|
| test_kiwoom_runtime_return_code.py | 5 OK |
| test_k2_bridge_evidence_integrity.py | 18 OK |
| test_k2_evidence_contract.py | 34 OK |
| test_reconcile_broker_state.py | 56 OK |
| test_kiwoom_broker_shadow.py | 24 OK |
| test_kiwoom_candidate_discovery.py | 10 OK |
| test_materialize_kiwoom_session_aware_acceptance_candidate.py | (pin scope 수정 전) 24개 중 실패 2·오류 14. 14개 오류와 `test_10`은 모두 `implementation hash mismatch: …/kiwoom_runtime_bridge.py`(acceptance 무효화, 예상). `test_12`는 `source artifact missing`(gitignore된 원본 산출물이 worktree에 없음, 변경 전에도 실패). pin scope 수정 뒤 결과는 11-2절 |

### 6-3. 스키마 감사

`python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → `{"status": "PASS", "errors": []}`.

### 6-4. 전체 스위트 (변경 전·후, 하위 에이전트, `.git` 없는 바이트 사본에서 같은 명령)

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"`. 두 사본의 차이는 바꾼 4개 파일뿐임을 하위 에이전트가 확인했다.

| | Ran | failures | errors | skipped |
|---|---|---|---|---|
| 변경 전 | 2468 | 26 | 284 | 4 |
| 변경 후 | 2483 | 28 | 297 | 4 |

- 늘어난 15개 테스트는 새 모듈이며 전부 통과.
- **변경 전 실패 246개 id(부분 테스트 포함 310건)는 모두 환경 원인이다.** `core.autocrlf=true` 때문에 디스크 파일이 CRLF가 되어, 원시 바이트 해시로 이름 붙인 산출물(identity·calendar authority, acceptance manifest)이 이름과 안 맞는다. 그 밖에 gitignore된 산출물이 없고, 사본에 `.git`이 없다. 원본 폴더에서는 결과가 다를 수 있다.
- **새 실패 15개(id 기준), 모두 예상된 결과:**
  - 14개 `test_materialize_kiwoom_session_aware_acceptance_candidate.KiwoomAcceptanceCandidateMaterializationTest`(test_01, 02, 03, 03a, 04, 06, 07, 08×3 부분 테스트, 09, 09a, 09b, 10): `current active Acceptance invalid beyond allowed drift: ['implementation hash mismatch: manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py']`
  - 1개 `test_v2_6_7_session_aware_kiwoom_priority.InvariantAndContractTests.test_provider_authority_change_starts_zero_count_cohort`: 저장된 `semantic_fingerprint` `4f11526e…` ≠ 다시 계산한 값 `3cdbd274…`(정책 파일 변경, 0절 3번)
- 고쳐진 것(변경 전 실패 → 변경 후 통과): 없음.
- 그 밖의 새 실패: 없음. 두 묶음은 재고정과 cohort 이전(8절 1·8·9번) 뒤에 풀린다.

## 7. 확인 필요

- 원본 폴더(`E:\사업\##금동한\코덱스저장소`)의 `workspace/state/integrated_shadow/shadow_progress.json` 카운터가 0인지(worktree 사본만 읽음).
- 예약 작업(Codex "Morning Portfolio Strategy" 등)이 지금 멈춰 있는지 — 문서상 PAUSED, 설정이 저장소 밖이라 코드로 확인 못 함. 멈춰 있지 않다면 다음 예약 실행도 바뀐 브리지를 쓴다(병합 뒤).
- `.env`의 `APP_KEY`와 별칭 키링 앱키가 같은지(비밀이라 확인하지 않음, 검토 문서 4절). 다르면 브리지가 별칭 쪽으로 통일된다. 실측 검증으로 확인.
- 키움 서버가 같은 앱키의 새 토큰 발급 때 이전 토큰을 무효화하는 규칙(검토 문서 1절, 문서 근거 없음).
- 외부 런타임 작업 트리에 로컬 수정이 없는지(`git status`는 worktree 격리 때문에 실행하지 않음; HEAD만 확인).
- 부모 CLI의 `--readonly-policy`로 다른 정책을 줄 때 별칭은 저장소 기본 정책에서 읽힌다(4절). 의도와 맞는지 Judge·사용자 판단.
- Windows에서 `FileTokenStore.save`의 `protect_file(strict=True)`(icacls)가 브리지 실행 계정에서도 성공하는지 — kiwoomcli는 같은 PC·계정에서 이미 저장하고 있으므로 같을 것으로 보이나 실측 전 미확인.
- (pin scope) 병합부터 재고정 materialize까지 **다른 고정 파일 25개 중 하나라도 main에서 바뀌면** materialize는 fail-closed로 거부한다(허용 목록이 두 파일뿐이므로 의도된 동작). 그때는 pin scope를 다시 K3로 고쳐야 한다. 병합 직전 main에 고정 파일 변경이 들어왔는지 Judge가 확인.
- (pin scope) 원본 폴더에서 materialize 테스트 test_05·test_12가 통과하는지 — source artifact 9개가 원본 폴더에 **있는 것**만 확인했고(원시 해시는 보지 않음), 원본 폴더에서 테스트는 돌리지 않았다(원본에는 아직 이 변경이 없음). 재고정 8절 6번의 바이트 사본 전체 스위트에서 확인.
- (pin scope) 새 acceptance가 활성화된 뒤에도 허용은 45cf에 묶여 있어 새 acceptance에 대해서는 아무것도 면제하지 않는다(fail-closed 기본값). 다음 재고정 때는 pin scope와 test_21의 고정값을 함께 K3로 바꿔야 한다.
- (pin scope) 지시문 문구는 "두 개만 **추가**"였지만 기존 6개에 추가하면 7개가 되어 "정확히 두 파일"과 맞지 않고, 기존 목록 중 manifest 스키마가 45cf에 대해 허용되는 만큼 넓어진다. 그래서 **교체**했고, 이 방식은 사용자가 직접 승인했다(2026-10-06).

## 8. 재고정 절차 (실행하지 않음, 별도 K3 단계)

1. ~~pin scope 수정~~ **이번 변경에 포함해 끝냄(사용자 승인 2026-10-06, 11절).** `allowed_drift_predecessor_sha256` = `45cf188892601d61c117519b4d34fc9e6b2ee82074489b8dd9cc0b661ca8bc80`, `allowed_predecessor_drift` = [`manage-us-stock-strategy/scripts/kiwoom_runtime_bridge.py`, `manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json`]. 4번 materialize가 만드는 후보의 `predecessor_implementation_drift`에는 이 두 파일이 기록될 것이다(코드 읽기 기준).
2. 이 Builder 변경에 대한 독립 Judge(별도 세션) → PASS면 사용자가 자기 터미널에서 커밋·병합.
3. 재고정 K3 시작(사용자 승인). **원본 폴더에서** 한다: worktree에는 gitignore된 원본 산출물이 없고 CRLF 때문에 원시 해시로 manifest를 찾는 테스트가 실패한다.
4. materialize 1회:
   `python manage-us-stock-strategy/scripts/materialize_kiwoom_session_aware_acceptance_candidate.py --active-priority-policy workspace/policies/kiwoom-session-aware-priority-policy.json --provider-scope-policy workspace/policies/kiwoom-session-aware-priority-policy.json --source-registry workspace/policies/source_capabilities.json --output-root workspace/research/provider-evidence/kiwoom/<YYYY-MM-DD> --generated-at <ISO 시각> --repository-base-commit <40자리 커밋>`
   (출력은 canonical evidence root 안이어야 하고, 쓴 뒤 검증하므로 실패하면 후보 파일이 남을 수 있다.)
5. 후보 검증: `python manage-us-stock-strategy/scripts/validate_kiwoom_session_aware_acceptance_candidate.py --manifest <후보> --manifest-schema manage-us-stock-strategy/schemas/kiwoom-session-aware-acceptance-manifest.schema.json --provider-scope-policy workspace/policies/kiwoom-session-aware-priority-policy.json --priority-schema manage-us-stock-strategy/schemas/kiwoom-session-aware-priority-policy.schema.json --source-registry workspace/policies/source_capabilities.json --source-schema manage-us-stock-strategy/schemas/source-capability.schema.json` → PASS 기대.
6. 바이트 사본에서 활성화 모의 + 전체 스위트(이전 R6·R9 선례).
7. 후보에 대한 독립 Judge → 사용자 커밋.
8. **활성화(정책 수정, 사용자 명시 승인):** `kiwoom-session-aware-priority-policy.json`의 `provider_scopes[*].acceptance_artifact_hash` 15곳과 `acceptance_evidence.session_aware_acceptance_manifest_sha256`, `source_capabilities.json`의 `kiwoom_rest.acceptance_artifact_sha256`를 새 ID로 바꾼다(포인터 17곳).
9. **shadow cohort 이전(상태 쓰기, 사용자 승인):** 카운터가 모두 0인지 확인한 뒤 `python manage-us-stock-strategy/scripts/migrate_integrated_shadow_cohort.py`. 포인터 교체로 fingerprint가 또 바뀌므로 8번 뒤 한 번만.
10. 확인: `python manage-us-stock-strategy/scripts/validate_kiwoom_session_aware_acceptance.py --manifest <새 manifest> …` PASS, `test_v2_6_7…`·materialize 테스트·전체 스위트·`validate_schema_contracts.py`.
11. 사용자 커밋(경로 명시 staging). "확인 <코드>" 절차는 해당 없음(대조·저널 apply 전용).

절차 출처: 하위 에이전트의 코드 조사(argparse·검증 함수 행 번호)와 `docs/claude` 이전 재고정 보고(R6·R9) 선례. 명령 인자는 각 스크립트 argparse와 맞춰 보았으나 실행하지는 않았다.

## 9. 실측 검증 절차 (사용자 PC, 병합·재고정 뒤)

1. `kiwoomcli auth login` → 2번(토큰만 재발급).
2. MCP 미체결 조회 → 정상.
3. 대조 propose 또는 수동 분석 1회(브리지 실행).
4. MCP 미체결 조회 → 8005가 없으면 통과.

추가로 보면 좋은 것: 3번 실행 결과에 `AUTHENTICATION_FAILURE`가 없는지. 통과하면 `portfolio-exposure-review.md`의 조건부 문장대로 토큰 순서·`auth refresh/login` 절차를 뺄 수 있다.

## 10. 보고 전 자기 점검 (fail-open 점검표)

별칭·자격을 못 찾으면 env 자격으로 넘어가지 않고 `KIWOOM_API_UNAVAILABLE`/`AUTHENTICATION_FAILURE`로 닫힌다(T6, 별칭 경로 변이 시험으로 확인) / 복구는 런타임 자체 복구까지 포함해 세션당 1회를 넘지 않고, 재전송 응답은 기존 `return_code` 검증을 그대로 거쳐 실패를 PASS로 바꾸지 않는다(T3·T4·T5) / mode는 `real` 고정·이중 확인이고, 주문 경로 목록은 바꾸지 않았으며, 새 경로는 이미 허용된 요청을 같은 대상으로 한 번 다시 보낼 뿐 권한을 넓히지 않는다.

## 11. 추가 변경 — pin scope 수정 (사용자 승인 2026-10-06, 결정 (가))

지시: 보고서 8절 1번 그대로, `kiwoom-acceptance-pin-scope.json`만 수정하고 기존 변경(브리지·정책·테스트)은 건드리지 않는다. 진행 중 Claude Code 권한 검사기가 수정 확인 명령을 "보안 약화"로 한 번 막았고, 사용자가 대화에서 직접 "pin scope 수정(가) 승인함. 교체 방식(허용 목록을 두 파일로 교체)도 승인함"이라고 다시 승인한 뒤 이어서 진행했다.

### 11-1. 수정 전 코드 확인 (읽기만, materialize 실행 안 함)

- materialize(`materialize_…:156`, `:171-185`)는 활성 acceptance를 `validate_acceptance`로 검증하고, 그 오류 중 `disallowed_predecessor_errors`(`validate_…_candidate.py:380-385`)가 `"implementation hash mismatch: " + 허용 경로`와 **정확히 같은 문자열**만 면제한다. 나머지 오류는 모두 거부.
- `validate_acceptance`(`validate_kiwoom_session_aware_acceptance.py:16-90`)는 활성 manifest의 `implementation_hashes`만 다시 해시하고, 활성 manifest 안의 `candidate_governance.pin_scope.sha256`은 검사하지 않는다. 그래서 pin scope 수정이 만드는 오류는 `implementation hash mismatch: …/kiwoom-acceptance-pin-scope.json` 한 줄뿐이며 허용 목록으로 면제된다.
- 후보 검증기(`validate_…_candidate.py:542-566`)도 같은 규칙이다: 활성 manifest 대비 drift 파일이 모두 허용 목록에 있어야 하고(`:547-549`), 후보가 기록한 drift가 실제 drift와 같아야 한다(`:550-554`).
- 45cf manifest(`workspace/research/provider-evidence/kiwoom/2026-10-05/45cf…/…candidate.json`, git 추적)는 evidence root에서 정규화 해시로 정확히 1개 찾아진다. 고정 27개 = 현재 `required_implementation_paths`. 정규화 해시 비교(작업 폴더 밖 scratch 스크립트, 쓰기 없음): **worktree drift = 브리지 1개, 원본 폴더 drift = 0개.** pin scope 수정 뒤 = 브리지 + pin scope 2개 → 허용 목록과 정확히 같다.
- 기존 허용 6개 중 `run_manual_portfolio_analysis.py`, `test_manual_portfolio_analysis.py`, materialize·후보 검증 스크립트 4개는 45cf가 고정하지 않으므로 빼도 아무것도 막지 않는다. manifest 스키마는 45cf가 고정하지만 바뀌지 않았으므로, 남겨 두면 허용만 넓어진다.
- 스키마(`kiwoom-acceptance-pin-scope.schema.json`) 경로 패턴 `^manage-us-stock-strategy/(scripts|schemas|tests|assets)/…`에 두 경로 모두 맞는다. `load_pin_scope`의 자기 고정·스키마 고정 검사는 `required_implementation_paths`를 보며, 이 목록은 바꾸지 않았다.

### 11-2. 테스트

- 새 `PinScopeAllowanceTest`(materialize 테스트 파일):
  - test_21: `allowed_drift_predecessor_sha256 == 45cf…`, `allowed_predecessor_drift ==` [브리지, pin scope] (순서까지), `allowed_drift_for(pin, 45cf)`가 같은 두 개, 45cf manifest가 evidence root에서 찾아지고 두 파일을 모두 고정함.
  - test_22: predecessor가 `f0bab…`(이전 값)·첫 글자만 바꾼 45cf·`0`×64·빈 문자열·None이면 허용 목록이 비고, 두 drift 오류가 그대로 거부 오류로 남음.
  - 검증력 점검(메모리 안 패치, 파일 쓰기 없음): 허용 목록에 manifest 스키마 추가 / `run_manual_portfolio_analysis.py` 재추가 / pin scope 제거 / predecessor를 f0bab로 되돌림 / `allowed_drift_for`가 predecessor를 무시 — 5종 모두 최소 1개 테스트 실패, 원상태 0개 실패.
- 기존 테스트 갱신: 필요 없었다. test_03a·test_10은 pin scope를 파일에서 동적으로 읽고, `SyntheticPredecessorDriftTest`(test_12-20)는 허용 값을 직접 덮어쓰므로 고정값에 의존하지 않는다.
- `test_materialize_kiwoom_session_aware_acceptance_candidate.py`(worktree): 수정 전 24개 중 실패 2·오류 14 → 수정 뒤 **26개 중 실패 1·오류 1.** 남은 둘(test_05, test_12)은 모두 `source artifact missing`(gitignore된 원본 산출물 9개가 worktree에 없음; 원본 폴더에는 9개 모두 있음, 존재만 확인). drift 때문에 생기던 오류 14건은 모두 풀렸다(test_10 포함).
- `test_kiwoom_token_reuse.py`: 15 OK.
- `validate_schema_contracts.py`: `{"status": "PASS", "errors": []}`.

### 11-3. 전체 스위트 (하위 에이전트, `.git` 없는 바이트 사본 2개, pin scope·테스트 파일 수정 전 대비)

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"`(사본마다 따로 TEMP). 수정 전 사본은 두 파일을 HEAD blob(`1a7c8ca2…`, `e74069ab…`)에서 LF→CRLF로 되살렸고, blob id 일치와 두 사본의 차이가 이 두 파일뿐임을 하위 에이전트가 확인했다.

| | Ran | failures | errors | skipped |
|---|---|---|---|---|
| pin scope 수정 전(= 6-4절 변경 후) | 2483 | 28 | 297 | 4 |
| pin scope 수정 후 | 2485 | 27 | 284 | 4 |

- **새 실패: 0.** 늘어난 2개는 test_21·22이며 통과.
- **고쳐진 것 14개(id 기준):** materialize `KiwoomAcceptanceCandidateMaterializationTest`의 test_01, 02, 03, 03a, 04, 06, 07, 08×3 부분 테스트, 09, 09a, 09b(오류 13), test_10(실패 1). 6-4절의 "새 실패 15개" 중 14개가 풀렸다.
- 남은 실패 311건은 두 사본에서 id·유형이 같다(환경 원인: `INTEGRITY_FAILURE` 273, 산출물 없음 8, `.git` 없음 2 등). 그중 test_05는 오류 이유가 drift → `source artifact missing`(환경)으로 바뀌었다. 6-4절의 나머지 새 실패 1개(`test_v2_6_7…test_provider_authority_change_starts_zero_count_cohort`, 정책 파일 변경)는 그대로이며 8절 8·9번(활성화·cohort 이전) 뒤에 풀린다.

### 11-4. 자기 점검

- 허용 목록이 두 파일을 넘지 않는가: **넘지 않는다.** 파일에 정확히 2개, test_21이 순서까지 고정하고, 추가하면 실패함을 변이로 확인.
- predecessor 해시가 틀리면 fail-closed로 남는가: **남는다.** `allowed_drift_for`가 해시가 다르면 빈 목록을 돌려주어 모든 drift가 거부 오류로 남는다(코드 `:372-377`, test_22, 기존 test_14). 새 acceptance가 활성화된 뒤에도 허용은 45cf에만 묶여 있어 아무것도 면제하지 않는다.
- 다른 파일은 바꾸지 않았다: 이번 단계에서 편집한 파일은 pin scope·materialize 테스트·이 보고서 셋뿐이고(브리지·정책·`test_kiwoom_token_reuse.py`·`portfolio-exposure-review.md`는 손대지 않음), pin scope의 `required_implementation_paths`·`pin_scope_id`·`description`·권한 필드 무변경. 두 파일 모두 CRLF 유지(LF만 있는 줄 0).
