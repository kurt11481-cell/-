# 키움 acceptance 재고정 후보 K3 Judge 지시문 (2026-10-07)

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(원본 폴더, 파일 수정 금지, worktree 불필요) · 이유: K3 Independent Judge — 활성화 전 새 acceptance 후보와 활성화 방법의 독립 검토

- 대상: 원본 폴더 `E:\사업\##금동한\코덱스저장소`, HEAD `332a11c8d98b19f4bd3d60b69cde06d2a7a3b986`.
- 후보: `workspace/research/provider-evidence/kiwoom/2026-10-07/835d4f46bb9e3532a79e32aca9a408f59861640b31dc04718cdb507f5f8e429c/session-aware-priority-acceptance-inactive-superseding-candidate.json` (커밋 전, untracked)
- Cowork 보고: `docs/claude/kiwoom-repin-candidate-report-2026-10-07.md` (자기보고이므로 증거가 아님)
- 적용 도구(활성화 때 쓸 것): `Claude outputs/kiwoom-repin-2026-10-07/repin_apply.py`
- 근거: `docs/claude/kiwoom-token-reuse-builder-report-2026-10-06.md` 8절, 선례 `docs/claude/i4-r9-activation-report-2026-10-05.md`(R9 활성화).

## 사용자 조작 (Windows 터미널)

1. `cd /d "E:\사업\##금동한\코덱스저장소"`
2. `claude` → `/model` Opus, `/effort` xhigh
3. 권한 창: 읽기, git 읽기 명령(status/diff/log/show), 테스트 실행, **작업 폴더 밖** scratch 폴더 쓰기는 허용. 원본 폴더 안 파일 수정·생성, 키움 접속, `kiwoomcli`, `.env`·토큰·키링 읽기, 커밋·푸시는 거부.
4. 아래 상자를 붙여 넣는다. 끝나면 Judge의 최종 보고(판정+발견 목록)를 그대로 Cowork에 붙여 넣는다.

## 붙여넣기용 지시문

```text
역할: 키움 acceptance 재고정 후보(835d4f46…) 독립 Judge (K3). 원본 폴더 E:\사업\##금동한\코덱스저장소 의 파일을 수정하지 않는다. 판정과 근거만 최종 메시지로 보고한다(한국어, 식별자는 영어, 70줄 이내).
금지: 원본 폴더 안 파일 수정·생성(검증용 스크립트·사본은 작업 폴더 밖 scratch에서만), 키움 실제 접속, kiwoomcli, .env*·토큰·키링·계좌번호 읽기·출력, 원본에서 materialize·repin_apply.py·migrate_integrated_shadow_cohort.py 실행, 커밋·푸시. Cowork 보고서(docs/claude/kiwoom-repin-candidate-report-2026-10-07.md)는 자기보고이므로 증거가 아니다 — 파일·코드·재실행으로 확인한다.
후보 경로 C = workspace/research/provider-evidence/kiwoom/2026-10-07/835d4f46bb9e3532a79e32aca9a408f59861640b31dc04718cdb507f5f8e429c/session-aware-priority-acceptance-inactive-superseding-candidate.json
이전 활성 45cf = workspace/research/provider-evidence/kiwoom/2026-10-05/45cf188892601d61c117519b4d34fc9e6b2ee82074489b8dd9cc0b661ca8bc80/session-aware-priority-acceptance-inactive-superseding-candidate.json

0. 범위
   - git status: 이번 단계의 새 파일이 후보 폴더 1개, docs/claude/kiwoom-repin-*-2026-10-07.md 2개, Claude outputs/kiwoom-repin-2026-10-07/ 뿐인가. workspace/policies, workspace/state, stock-strategy-system, pin scope의 고정 27개 경로가 HEAD와 같은가(diff 0).
   - 정책 2개(kiwoom-session-aware-priority-policy.json, source_capabilities.json)가 아직 45cf를 17곳(소문자 15·대문자 1, 대문자 1) 가리키고 835d는 0곳인가.

1. 후보 파일
   - 원시 sha256 = 835d4f46…, LF 1, CR 0, BOM 없음.
   - 후보 검증기 재실행: python manage-us-stock-strategy/scripts/validate_kiwoom_session_aware_acceptance_candidate.py --manifest C --manifest-schema manage-us-stock-strategy/schemas/kiwoom-session-aware-acceptance-manifest.schema.json --provider-scope-policy workspace/policies/kiwoom-session-aware-priority-policy.json --priority-schema manage-us-stock-strategy/schemas/kiwoom-session-aware-priority-policy.schema.json --source-registry workspace/policies/source_capabilities.json --source-schema manage-us-stock-strategy/schemas/source-capability.schema.json → PASS인가.

2. 결정성(OS 독립) — 후보는 Cowork 리눅스 VM의 Python 3.13에서 만들어졌다.
   - Windows Python에서 쓰기 없이 materialize 모듈의 build_candidate_manifest(active_priority_policy_path=정책, provider_scope_policy_path=정책, source_registry_path=source_capabilities, repo_root=원본, generated_at="2026-10-07T15:29:50+09:00", repository_base_commit="332a11c8d98b19f4bd3d60b69cde06d2a7a3b986")를 메모리 안에서 호출해(sys.dont_write_bytecode=True) 반환 바이트가 C의 원시 바이트와 같고 sha가 835d4f46…인지 확인. 다르면 차이 키를 보고(FAIL 사유).

3. 내용
   - implementation_hashes 키 = pin scope required_implementation_paths 27개와 정확히 같고, 각 값이 현재 원본 파일의 정규화 해시(코드의 normalized_sha256 그대로)와 같은가.
   - 45cf 대비: 바뀐 implementation_hashes가 kiwoom_runtime_bridge.py·kiwoom-acceptance-pin-scope.json 2개뿐이고, candidate_governance.predecessor_implementation_drift가 정확히 그 2개(pinned = 45cf 값, current = 현재 값)인가. supersedes_acceptance_sha256 = 45cf…인가. 그 밖에 바뀐 키(generated_at, repository_base_commit, candidate_governance의 authority_bindings·pin_scope·provider_scope)가 모두 설명 가능한가.
   - authority_bindings 해시가 현재 정책·등록부·45cf의 정규화 해시와 같은가. provider_scope 15종목과 순서가 정책과 같은가.
   - 권한: order_authority false, quantity_authority none, execution_quantity null, activation_performed false, candidate_status INACTIVE_SUPERSEDING_CANDIDATE.
   - repository_base_commit 332a11c가 존재하고 그 커밋의 고정 27개 blob이 작업 트리와 (정규화 기준) 같은가.

4. 적용 도구 검토 (Claude outputs/kiwoom-repin-2026-10-07/repin_apply.py, 읽기만)
   - 원시 바이트에서 같은 대소문자의 64자 해시만 바꾸는가. 개수(priority 15+1, source 0+1, 합계 17), 새 해시 사전 0곳, 크기·CRLF·LF 개수 불변, JSON 경로 diff = 17, 권한 필드 불변을 단언하는가. --apply 없으면 쓰지 않는가. 쓰기 직전 파일이 바뀌지 않았는지 다시 보는가. 빠진 단언이나 fail-open 경로가 있으면 지적.

5. Windows 사본 모의 (작업 폴더 밖 scratch, R9 보고 2절 선례)
   - robocopy로 원본을 사본 2개(base, sim)로 복사(.claude/worktrees, .runtime-cache 제외, .git 포함). 두 사본이 추적 파일 원시 바이트까지 같은지 확인.
   - sim에만: (a) python "<원본>\Claude outputs\kiwoom-repin-2026-10-07\repin_apply.py" <sim> 45cf188892601d61c117519b4d34fc9e6b2ee82074489b8dd9cc0b661ca8bc80 835d4f46bb9e3532a79e32aca9a408f59861640b31dc04718cdb507f5f8e429c --apply  (b) 적용 직전 sim의 shadow_progress.json 카운터 0 확인 후 python <sim>\manage-us-stock-strategy\scripts\migrate_integrated_shadow_cohort.py --repo-root <sim> --reason SESSION_AWARE_KIWOOM_PROVIDER_AUTHORITY_CHANGE
   - 확인: sim에서 운영 검증기(validate_kiwoom_session_aware_acceptance.py --manifest <sim의 C> … --repo-root <sim>) PASS, 45cf로는 FAIL. sim의 shadow_progress.json이 CRLF 28줄·LF만 있는 줄 0으로 유지되는가. 보관 파일 cohorts/integrated-shadow-a0d3e69e9bc23a1b/superseded_progress.json 생성, reason 값. base·sim 차이가 정책 2개·shadow_progress.json·보관 파일뿐인가.
   - 대상 테스트(base·sim 각각): test_v2_6_7_session_aware_kiwoom_priority, test_materialize_kiwoom_session_aware_acceptance_candidate, test_kiwoom_token_reuse, test_migrate_integrated_shadow_cohort, test_scheduled_input_gate + validate_schema_contracts.py.
   - 전체 스위트는 서브에이전트에서 base·sim 따로(TEMP 분리): python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py". sim의 새 실패 0, v2_6_7 acceptance 2건 해소를 기대. 실패 id 차이만 보고.

6. 남은 위험 판단 (각각 수용 가능/조건 필요)
   - (a) 8번(포인터 교체)과 9번(이관) 사이에 record_integrated_shadow_attempt가 돌면 보관 없이 새 cohort가 시작되고 migrate는 COHORT_ALREADY_CURRENT를 낸다(shadow_acceptance.py 해당 줄 확인). 8→9를 연달아 하면 충분한가.
   - (b) scheduled_input_gate.py 배포 출처 검사가 활성화 뒤 예약 런타임 clone 경로에서 CURRENT_PROVIDER_SCOPE_HASH_MISMATCH·CURRENT_SEMANTIC_COHORT_MISMATCH를 낼 수 있는가(그 경로는 보류 중, r-sched-b 문서). 운영 수동 경로에는 영향이 없는가.
   - (c) 활성화 뒤 pin scope 허용(45cf에 묶임)이 새 acceptance에 대해 아무것도 면제하지 않는가(allowed_drift_for).
   - (d) git core.autocrlf=true에서 후보 파일 LF를 어떻게 지키나: 커밋 뒤 checkout이 CRLF로 바꾸면 원시 해시가 바뀐다. 활성 manifest를 원시 해시로 찾는 코드·테스트가 있는지 grep(예: test_v2_6_7 helper). 필요한 조건(.gitattributes 등)은 제안만 하고 만들지 않는다.

판정: PASS / PASS-WITH-CONDITIONS / FAIL. 각 발견은 [심각도 H/M/L] 파일:줄 — 사실 — 필요한 최소 조치(또는 수용 이유) 한 줄. FAIL이면 최소 조치만 적는다(재설계 제안 금지). 마지막에 "활성화 전 사용자가 할 일"을 한 줄로 적는다.
보고 전 자기 점검: Cowork 보고를 증거로 쓴 곳은 없는가? 실행하지 못한 확인은 "확인 필요"로 적었는가? 원본 폴더에 쓴 파일이 없는가(git status로 확인)?
```

## 다음 단계

- Judge PASS(또는 조건부 PASS) → 사용자가 후보 파일·보고서·이 지시문을 경로 지정으로 커밋 → Cowork에서 8번 활성화 승인 요청.
- FAIL → Cowork가 원인을 보고하고, 후보를 다시 만들어야 하면 새 날짜 폴더로 materialize(기존 후보는 지우지 않음).
