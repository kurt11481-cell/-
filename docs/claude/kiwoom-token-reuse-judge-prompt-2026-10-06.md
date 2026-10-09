# 키움 토큰 재사용 K3 Judge 지시문 (2026-10-06)

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(Builder 창과 분리, 파일 수정 금지) · 이유: K3 Independent Judge — 인증 경로와 acceptance 고정 파일 2개를 바꾼 변경의 독립 검토

- 대상: worktree `E:\사업\##금동한\코덱스저장소\.claude\worktrees\kiwoom-token-reuse` (커밋 전 변경). 기준 HEAD `782d61b`.
- Builder 보고: 그 worktree의 `docs/claude/kiwoom-token-reuse-builder-report-2026-10-06.md` (자기보고이므로 증거로 쓰지 말고 diff·코드·테스트로 확인)
- 근거 문서: 메인 폴더 `docs/claude/kiwoom-token-reuse-review-2026-10-06.md`, `kiwoom-token-reuse-builder-prompt-2026-10-06.md`
- 사용자 승인(Builder 단계): "A + 1회 자동 복구", "pin scope 수정(가) + 교체 방식".

## 사용자 조작 (Windows 터미널)

1. `cd "E:\사업\##금동한\코덱스저장소\.claude\worktrees\kiwoom-token-reuse"`
2. `claude` → `/model` Opus, `/effort` xhigh
3. 권한 창: 읽기·git 읽기 명령(status/diff/log/show)·테스트 실행은 허용. 파일 수정·쓰기, 키움 접속, `kiwoomcli`, `.env`·토큰·키링 읽기, 커밋·푸시는 거부.
4. 아래 상자를 붙여 넣는다. 끝나면 Judge의 최종 보고(판정+발견 목록)를 그대로 Cowork에 붙여 넣는다.

## 붙여넣기용 지시문

```text
역할: kiwoom-token-reuse 독립 Judge (K3). 파일을 수정하지 않는다. 판정과 근거만 최종 메시지로 보고한다(한국어, 식별자는 영어, 60줄 이내).
금지: 파일 수정·생성(검증용 스크립트는 작업 폴더 밖 scratch에서만, 쓰기는 거기에만), 키움 실제 접속, kiwoomcli 실행, .env*·토큰 파일·키링·계좌번호 읽기·출력, materialize/activate/apply 실행, 커밋·푸시. Builder 보고서는 자기보고이므로 증거가 아니다 — 모든 결론은 diff·코드·테스트 재실행으로 확인한다.

0. 범위 확인
   - git status/diff로 변경 파일이 정확히 이 7개인지 확인: kiwoom_runtime_bridge.py, kiwoom-readonly-policy.json, portfolio-exposure-review.md, test_kiwoom_token_reuse.py(새), kiwoom-acceptance-pin-scope.json, test_materialize_kiwoom_session_aware_acceptance_candidate.py, builder 보고서(새). 그 밖의 변경이 있으면 FAIL 사유.
   - kiwoom_account_readonly_bridge.py, kiwoom_candidate_discovery_bridge.py, 주문 경로(BLOCKED_TERMS, RUNTIME_APIS, ALLOWED_OPERATIONS, blocked_api_target)가 무변경인지 diff로 확인.

1. 토큰 공유(A) — fail-open 점검
   - _runtime_session이 정책 token_profile_alias로만 get_auth(mode="real", profile=…, token_store_kind="file")를 부르는가? 별칭 없음/빈 값/잘못된 JSON/자격 없음/mode≠real일 때 env 자격으로 조용히 넘어가는 경로가 있는가? has_credentials 확인 누락 경로는?
   - 무조건 refresh_access_token() 호출이 남아 있는가(oauth_health 포함)?
   - 외부 런타임(E:\사업\##금동한\runtime\Kiwoom-REST-API, commit 69642586) auth.py·token_store.py·secrets.py·runtime.py·client.py를 읽어 Builder가 적은 동작(만료 10분 전 버퍼, 자격 None이면 지문 비교 생략, FileTokenStore 원자적 교체, fetch_page 자체 복구)이 사실인지 확인.

2. 1회 자동 복구(B)
   - 판정 함수(_auth_failure)가 HTTP 401, return_code 8005/8031/8103, return_code 3 + "[8005:" 등만 잡는가? 429·일반 오류를 잘못 복구하지 않는가?
   - 복구가 워커 세션당 정말 1번인가(런타임 fetch_page 자체 복구와 겉면 복구가 합쳐서 1번)? 재전송 응답이 기존 return_code·스키마 검증을 그대로 통과해야 하는가? 복구 성공을 PASS로 가장하는 경로는?
   - 재전송 전 pacer 대기, 두 번째 실패 시 AUTHENTICATION_FAILURE + 회로 차단.
   - 토큰·return_msg가 결과·로그·stdout·stderr·예외 메시지에 새지 않는가(test_kiwoom_token_reuse T7이 실제로 그것을 잡는 테스트인지 직접 읽고 판단).

2b. Builder가 5-1절에 적은 동작 변화 5개를 각각 수용 가능/수정 필요로 판정하고 이유를 쓴다. 특히: (3) oauth_health.authenticated 의미 약화(서버 왕복 없이 True 가능) — provider preflight나 증거에서 "인증 성공"을 서버 수용의 증거로 쓰는 곳이 있는가? (4) invoke_bridge 워커 재실행 시 복구가 호출당 최대 2번 — 수용 가능한가? (정책 별칭을 부모 --readonly-policy와 무관하게 저장소 기본 정책에서 읽는 점 포함.)

3. pin scope 수정
   - 허용 목록이 정확히 [kiwoom_runtime_bridge.py, kiwoom-acceptance-pin-scope.json]이고 predecessor가 45cf188892601d61c117519b4d34fc9e6b2ee82074489b8dd9cc0b661ca8bc80인가? required_implementation_paths 등 다른 필드 무변경(원본 대비 diff)?
   - 독립 재현: 45cf manifest(workspace/research/provider-evidence/kiwoom/2026-10-05/45cf…, git 추적)가 고정한 27개 경로의 정규화 해시(NORMALIZED_TEXT_SHA256, 코드의 정규화 함수를 그대로 사용)를 worktree·원본 폴더 각각에서 다시 계산해, 45cf 이후 바뀐 고정 파일이 브리지와 pin scope뿐인지 직접 확인(scratch 스크립트, 읽기 전용).
   - 교체(추가 아님)로 이전 항목 4개가 빠진 것이 다른 코드·테스트·문서에 영향을 주는가(allowed_predecessor_drift를 읽는 모든 곳 grep)?
   - predecessor가 다르면 fail-closed(allowed_drift_for), 새 acceptance 활성화 뒤에도 허용이 45cf에만 묶이는가?

4. 테스트
   - 새 테스트 test_kiwoom_token_reuse.py와 기존 대상 테스트(test_kiwoom_runtime_return_code, test_k2_bridge_evidence_integrity, test_k2_evidence_contract, test_reconcile_broker_state, test_kiwoom_broker_shadow, test_kiwoom_candidate_discovery, test_materialize_…)를 직접 재실행(unittest discover -s manage-us-stock-strategy/tests -p "test_<name>.py")하고 validate_schema_contracts.py도 실행. 환경(CRLF·gitignore 산출물 없음) 때문에 실패하는 것과 변경 때문에 실패하는 것을 구분하고, "변경 전에도 실패"는 HEAD 사본(git stash 금지, git worktree 새로 만들지 말고 `git show`로 읽기만)과 비교해 근거를 댄다. 전체 스위트는 서브에이전트에서.
   - 새 테스트가 브리지의 핵심 줄을 지워도 통과하는지(변이)를 대표 3개 정도 메모리 안에서 직접 시험한다.

5. 부수 확인
   - 원본 폴더 workspace/state/integrated_shadow/shadow_progress.json 카운터가 모두 0인지(읽기 전용; 0이 아니면 재고정 때 손실 위험이므로 보고).
   - portfolio-exposure-review.md 추가 문장이 "적용·실측 확인 전까지는 기존 절차 유지"로 오해 없이 조건부인지.
   - 같은 앱키 새 토큰이 이전 토큰을 무효화한다는 서버 규칙은 문서 근거가 없다("확인 필요")는 점이 보고서·판정에서 사실처럼 쓰이지 않는지.
   - 동시 실행 금지(브리지 실행 중 kiwoomcli 사용 금지) 규칙이 공유 파일 토큰으로 바뀐 뒤에도 문서에 남아 있는지.

판정: PASS / PASS-WITH-CONDITIONS / FAIL. 각 발견은 [심각도 H/M/L] 파일:줄 — 사실 — 필요한 최소 수정(또는 수용 이유) 한 줄. FAIL이면 같은 Builder에서 고칠 최소 수정만 적는다(재설계 제안 금지). 마지막에 실측 검증(사용자 PC) 4단계를 그대로 확인하고, 병합 전 사용자가 해야 할 일을 한 줄로 적는다.
보고 전 자기 점검: 내가 Builder의 말을 증거로 쓴 곳은 없는가? 읽지 못한 파일은 "확인 필요"로 적었는가?
```

## 다음 단계

Judge PASS → 사용자가 자기 터미널에서 커밋·병합(경로 명시 staging) → 재고정 K3(보고서 8절 3~11) → 실측 검증.
