# 키움 토큰 재사용 K3 Builder 지시문 (2026-10-06)

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree (`claude --worktree kiwoom-token-reuse`) · 이유: K3 — 키움 acceptance 고정 파일(`kiwoom_runtime_bridge.py`)과 정책 파일을 바꾸는 인증 경로 변경

- 근거: `docs/claude/kiwoom-token-reuse-review-2026-10-06.md`(진단). 사용자 승인 2026-10-06: **"A + 1회 자동 복구로 진행 승인"** — 정책 파일 별칭 키 추가와 acceptance 무효화(재고정은 별도 단계)를 알고 승인함.
- 기준: HEAD `e81472253263`. 기준 blob — `kiwoom_runtime_bridge.py` `28837ecbf79552e61867d632ff3a887a7e545441`, `kiwoom_account_readonly_bridge.py` `8063406960f6c1efc1d76cf04b7ae2ae46ea6e63`, `workspace/policies/kiwoom-readonly-policy.json` `55bf7f34c06f1d0d00d88ab33813a27d1440c0c7`, `assets/kiwoom-acceptance-pin-scope.json` `1a7c8ca2f3654f9b0c3cabc0d23edac3b4146f69`. 다르면 차이를 보고하고 멈춘다.
- 상태: 작성 완료, Builder 미실행. Judge 지시문은 Builder 보고 뒤 Cowork가 쓴다.

## 1. 사용자 조작 (Windows 터미널)

1. `cd "E:\사업\##금동한\코덱스저장소"`
2. 문서 2개 커밋(worktree는 커밋된 HEAD에서 만들어진다):
   `git add docs/claude/kiwoom-token-reuse-review-2026-10-06.md docs/claude/kiwoom-token-reuse-builder-prompt-2026-10-06.md`
   `git commit -m "docs: kiwoom token reuse review and builder prompt"`
3. `claude --worktree kiwoom-token-reuse`
4. 세션 안에서 `/model` → Opus, `/effort` → xhigh
5. 붙여 넣기: `docs/claude/kiwoom-token-reuse-builder-prompt-2026-10-06.md 2절 상자 안의 지시를 그대로 따르는 Builder로 일해라.`
6. 권한 창: 읽기·대상 파일 수정·테스트 실행은 허용. 키움 실제 접속, `kiwoomcli` 실행, `.env`·토큰·키링 읽기, 커밋·푸시는 거부.
7. 끝나면 보고 파일 경로를 Cowork에 알린다. Builder 창은 닫지 않는다(수정 때 다시 씀).

## 2. 붙여넣기용 지시문

```text
역할: kiwoom-token-reuse Builder (K3, 사용자 승인 2026-10-06 "A + 1회 자동 복구로 진행 승인").
먼저 읽기: docs/claude/kiwoom-token-reuse-review-2026-10-06.md 전체, CLAUDE.md Hard safety.
금지: 키움 실제 접속(테스트는 가짜 auth/client만), kiwoomcli 실행, .env*·토큰 파일·키링·계좌번호 읽기·출력, 주문 경로 변경(blocked_api_target·BLOCKED_TERMS·RUNTIME_APIS 목록 그대로), acceptance 후보 생성·활성화(materialize/activate 실행 금지), 외부 런타임(E:\사업\##금동한\runtime\Kiwoom-REST-API) 수정, 커밋·푸시, 줄바꿈 일괄 변환(CRLF 유지).
없는 사실은 만들지 않는다(확인 필요). 보고는 한국어, 식별자는 영어.

0. 기준 확인: 지시문 머리의 HEAD·blob 4개가 맞는지 git rev-parse로 확인. 다르면 보고하고 멈춘다.

1. 사실 확인(코드 읽기만)
   - manage-us-stock-strategy/scripts 안에서 kiwoom_runtime_bridge._runtime_session을 쓰는 모든 호출처(최소 kiwoom_runtime_bridge.external_worker, kiwoom_account_readonly_bridge 274행 근처, kiwoom_candidate_discovery_bridge 여부)와 각자가 읽는 정책 파일.
   - 외부 런타임 kiwoom/core/runtime.py get_auth(profile, token_store_kind), auth.py get_access_token / refresh_access_token / recover_from_auth_failure / _load_valid_token(만료 10분 전 버퍼, 자격 지문 불일치 시 clear), token_store.py FileTokenStore(원자적 교체), secrets.py default_secret_provider(profile 지정 시 별칭 키링만 사용), client.py 84행(return_code 8005·8031·8103만 자동 재시도 — 실제 응답은 return_code 3 + return_msg 안의 "[8005:" 라서 걸리지 않음).
   - 계좌 별칭 값: 문서상 "실전계좌"(docs/claude/s7-builder-report-2026-10-01.md 989행). 외부 런타임 profiles 모듈에 별칭 목록만 돌려주는 읽기 전용 함수가 있으면 그것으로 존재만 확인한다(키·비밀 값은 절대 읽지 않음). 확인할 수 없으면 "확인 필요"로 두고 계속한다.
   - 브리지 실패 분류(_exception_failure, immediate_open_failure_types, kiwoom-rate-limit-policy.json)에서 인증 실패가 어디서 AUTHENTICATION_FAILURE가 되고 회로가 열리는지.

2. 변경 A — 토큰 공유
   - workspace/policies/kiwoom-readonly-policy.json에 키 하나만 추가: "token_profile_alias": "<1단계에서 확인한 별칭>". 다른 키는 건드리지 않는다. 정책 스키마나 정책 해시를 검사하는 코드·테스트가 있으면 같이 맞추고 보고한다.
   - _runtime_session: get_auth(profile=<정책의 token_profile_alias>, token_store_kind="file") 후 auth.get_access_token()으로 토큰 확보(유효한 파일 토큰 재사용, 없거나 만료 10분 전일 때만 발급 → 같은 파일에 저장). refresh_access_token()을 무조건 호출하지 않는다.
   - 별칭 키가 없거나 비었거나 해당 별칭 자격 증명을 찾지 못하면 fail-closed(지금과 같은 KIWOOM_API_UNAVAILABLE 계열, 새 토큰을 env 자격으로 받는 대체 경로 금지).
   - 모든 호출처가 같은 별칭을 쓰게 한다(가장 작은 변경: 정책 값을 인자로 넘기거나 같은 정책에서 읽기 — 선택과 이유 보고).
   - mode는 real 고정 유지. 별칭의 mode가 real이 아니면 fail-closed.

3. 변경 B — 1회 자동 복구
   - 인증 실패 판정: HTTP 401, return_code ∈ {8005, 8031, 8103}, 또는 return_code 3이면서 return_msg에 "[8005:" "[8031:" "[8103:" 중 하나가 있는 경우. 판정 함수는 하나로 두고 메시지·토큰 값을 결과에 싣지 않는다.
   - 워커 세션 1회당 최대 1번만: auth.recover_from_auth_failure()(공유 파일 토큰을 지우고 새로 받아 같은 파일에 저장) → 그 요청을 1번만 다시 보낸다. 세션 플래그로 두 번째 복구를 막는다.
   - 재시도도 실패하면 지금 동작 그대로 AUTHENTICATION_FAILURE + 회로 차단(나머지 요청 KIWOOM_CIRCUIT_OPEN). 복구 성공 뒤의 응답도 기존 return_code 검증을 그대로 통과해야 한다.
   - 재시도는 pacer(요청 간격)를 지킨다. HTTP 429는 복구 대상이 아니다.
   - 출력·증거에 남길 수 있는 것은 "auth_recovery_attempted: true/false" 수준까지(새 필드가 스키마 계약에 걸리면 넣지 말고 보고).

4. 테스트(가짜 auth/client, 네트워크 없음) — 새 파일 manage-us-stock-strategy/tests/test_kiwoom_token_reuse.py
   - T1 유효한 파일 토큰이 있으면 발급 호출 0회.
   - T2 토큰이 없거나 만료 임박이면 발급 1회, 같은 저장소에 저장.
   - T3 return_code 3 + "[8005:" 응답 → 복구 1회 → 재시도 성공 → 결과 PASS.
   - T4 복구 뒤에도 인증 실패 → AUTHENTICATION_FAILURE, 남은 요청 CIRCUIT_OPEN, 복구 호출은 정확히 1회.
   - T5 같은 세션에서 두 번째 인증 실패가 나도 복구를 다시 하지 않음.
   - T6 별칭 키 없음/빈 값/자격 없음 → fail-closed, 발급 호출 0회.
   - T7 결과 JSON·stdout·stderr 어디에도 토큰 값(가짜 토큰 문자열)이 나오지 않음.
   - T8 HTTP 429는 복구하지 않음.
   - 기존 대상 테스트: test_kiwoom_runtime_return_code.py, test_k2_bridge_evidence_integrity.py, test_k2_evidence_contract.py, test_reconcile_broker_state.py, test_kiwoom_broker_shadow.py, test_kiwoom_candidate_discovery.py, test_materialize_kiwoom_session_aware_acceptance_candidate.py.
   - 실행: 대상 테스트 → python manage-us-stock-strategy/scripts/validate_schema_contracts.py → 전체 스위트는 서브에이전트에서 돌리고 실패만 보고(변경 전 실패와 비교).

5. acceptance 영향 조사(실행 말고 조사만)
   - kiwoom_runtime_bridge.py와 정책 파일 변경으로 현재 활성 acceptance가 어떤 검증에서 실패하는지, 그 실패가 materialize 스크립트가 허용하는 "pin scope 안의 구현 drift"에 해당하는지 코드로 확인.
   - acceptance가 무효인 동안 막히는 것(수동 분석 preflight, 대조 propose, 예약 작업 등)을 목록으로. 막히는 것이 있으면 보고 맨 위에 적는다(병합 전 사용자 결정 필요).
   - 재고정 절차(명령·순서·사용자 확인이 필요한 지점)를 적되 실행하지 않는다.

6. 문서(K0)
   - manage-us-stock-strategy/references/portfolio-exposure-review.md Routine 서두의 토큰 절차 문단: "적용·실측 확인 전까지는 기존 절차 유지, 확인 뒤에는 브리지가 kiwoomcli와 같은 토큰을 재사용하므로 auth login 불필요"로 조건부 갱신. 다른 문장은 건드리지 않는다.

보고: docs/claude/kiwoom-token-reuse-builder-report-2026-10-06.md (한국어)
- 맨 위: acceptance 무효 중 막히는 것(5단계) — 없으면 "없음".
- 바뀐 파일·줄 수, 별칭 확인 결과, 호출처 목록과 선택한 전달 방식, 테스트 결과(전·후 실패 id), 스키마 감사, 확인 필요.
- 실측 검증 절차(사용자 PC): ① kiwoomcli auth login → 2번 ② MCP 미체결 조회 정상 ③ 대조 propose 또는 수동 분석 1회 ④ MCP 미체결 조회에 8005 없음.
- 보고 전 자기 점검 한 줄(fail-open 점검표): 별칭·자격을 못 찾을 때 env 자격으로 조용히 넘어가지 않는가? 복구 경로가 1회를 넘거나 실패를 PASS로 바꾸지 않는가? 대체 경로가 권한을 넓히지 않는가(mode real 고정, 주문 경로 불변)?
```

## 3. 다음 단계

- Builder 보고 → Cowork가 사전 확인 후 Judge 지시문 작성 → 별도 세션 Judge → PASS면 사용자 커밋·병합 → acceptance 재고정(별도 K3 단계, 사용자 확인) → 실측 검증.
