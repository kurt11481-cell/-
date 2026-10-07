---
id: kiwoom-repin-candidate-report-2026-10-07
type: cowork-report
status: current
as_of: 2026-10-07
summary: s-token-repin(빌더 보고 8절) 3~7번 결과. 원본 폴더에서 새 키움 acceptance 후보 835d4f46…를 만들고 후보 검증 PASS. 사본 활성화 모의에서 새 실패 0, v2_6_7 acceptance 2건 해소. 원본 정책·상태는 그대로(45cf 활성). Judge PASS-WITH-CONDITIONS(8절), 적용 도구 v2로 조건 반영. 활성화(8번)·cohort 이전(9번)은 사용자 커밋·승인 대기.
consumers: [kiwoom-repin-judge-prompt-2026-10-07.md(독립 Judge), kiwoom-repin-judge-report-2026-10-07.md, s-token-repin 활성화 단계(8절 8~11), 개발 관제판 s-token-repin]
---

# 키움 acceptance 재고정 — 후보 생성·검증 보고 (2026-10-07, Cowork)

**결론:** 새 후보 `835d4f46bb9e3532a79e32aca9a408f59861640b31dc04718cdb507f5f8e429c` 생성·검증 PASS. 사본에서 활성화를 모의하니 새 실패 0, 기대한 2건 해소. 원본의 정책 2개·shadow 상태는 바꾸지 않았다. 다음은 독립 Judge.

근거: `kiwoom-token-reuse-builder-report-2026-10-06.md` 8절. 사용자 요청 2026-10-07 "키움 승인 기록을 새 코드에 다시 맞추기 진행"(재고정 K3 시작). 정책 포인터 교체·cohort 이전은 이 요청에서 실행하지 않았다(사용자가 단계별 승인으로 지정).

## 1. 실행 환경

- 원본 폴더 `E:\사업\##금동한\코덱스저장소`, 브랜치 `codex/master-recovery-expansion`, HEAD `332a11c8d98b19f4bd3d60b69cde06d2a7a3b986`.
- Cowork 리눅스 VM(사용자 PC 안)에서 원본 폴더를 마운트해 실행했다. Python 3.13.15(uv로 VM에 설치). VM 기본 Python 3.10은 정책의 7자리 소수초 시각(`2026-08-14T13:48:12.0562388+00:00`)을 읽지 못해 정책 스키마 검증이 실패하므로 쓰지 않았다(쓰기 없이 실패). `PYTHONDONTWRITEBYTECODE=1`로 `__pycache__`를 만들지 않았다.
- 후보 바이트는 `canonical_json_bytes` + 바이너리 쓰기(`open("xb")`), 해시는 정규화 방식이라 코드상 OS와 무관하다. Windows에서 같은 입력이 같은 바이트를 내는지는 Judge가 확인한다(지시문 2번).

## 2. 사전 확인 (쓰기 없음)

| 확인 | 결과 |
|---|---|
| 활성 binding | `45cf…` 17곳: priority policy 소문자 15·대문자 1, `source_capabilities.json` 대문자 1. 새 해시 0곳 |
| 45cf 이후 고정 27개 drift(정규화 해시) | `kiwoom-acceptance-pin-scope.json`, `kiwoom_runtime_bridge.py` 2개뿐 = 허용 목록과 같음. i0b 병합(`6bd5c5a`)은 고정 파일을 건드리지 않음 |
| git status(`workspace/policies`, `workspace/state`, `stock-strategy-system`, `manage-us-stock-strategy/{scripts,schemas,assets,tests}`) | 0줄 |
| `shadow_progress.json` | cohort `integrated-shadow-a0d3e69e9bc23a1b`, 정수 카운터 모두 0, 목록 모두 빔, `baseline_overlay_sessions` 0, `last_attempt_hash` null. CRLF 28줄 |
| 저장 지문 = 재계산 지문 | `a0d3e69e…` 일치 |
| 메모리 안 dry-run | `build_candidate_manifest`를 쓰기 없이 호출해 통과 확인 후 실제 실행 |

## 3. materialize·후보 검증 (8절 4~5)

명령(원본 폴더):

```
python manage-us-stock-strategy/scripts/materialize_kiwoom_session_aware_acceptance_candidate.py --active-priority-policy workspace/policies/kiwoom-session-aware-priority-policy.json --provider-scope-policy workspace/policies/kiwoom-session-aware-priority-policy.json --source-registry workspace/policies/source_capabilities.json --output-root workspace/research/provider-evidence/kiwoom/2026-10-07 --generated-at 2026-10-07T15:29:50+09:00 --repository-base-commit 332a11c8d98b19f4bd3d60b69cde06d2a7a3b986
```

- 결과 `status: PASS`, `write_status: CREATED`, `superseded_implementation_drift` = [pin scope, bridge].
- 후보: `workspace/research/provider-evidence/kiwoom/2026-10-07/835d4f46bb9e3532a79e32aca9a408f59861640b31dc04718cdb507f5f8e429c/session-aware-priority-acceptance-inactive-superseding-candidate.json`
  - 원시 sha256 = ID, 10077 bytes, LF 1, CR 0, BOM 없음. git에는 새 폴더 1개(untracked).
- 45cf 대비 바뀐 최상위 키: `generated_at`, `repository_base_commit`, `supersedes_acceptance_sha256`(f0bab → 45cf), `implementation_hashes`(27개 중 bridge·pin scope 2개), `candidate_governance`(`authority_bindings`, `pin_scope`, `predecessor_implementation_drift`, `provider_scope`). 추가·삭제된 키 없음.
- provider scope 15종목, 정책과 같은 순서: SOXL, MVLL, NBIS, BE, TOST, NOW, FSLY, SOXX, MRVL, AAPL, IBM, PGR, JPM, CME, V.
- 권한: `order_authority` false, `quantity_authority` none, `execution_quantity` null, `activation_performed` false, `candidate_status` INACTIVE_SUPERSEDING_CANDIDATE.
- 후보 검증 CLI(8절 5번 명령 그대로): `{"status": "PASS", "errors": []}`.

## 4. 사본 활성화 모의 (8절 6)

- 사본: VM 홈의 `base`·`sim`(원본에서 rsync). 뺀 것: `.claude/worktrees`, `.runtime-cache`, `.tmp`, `Claude outputs`, `%SystemDrive%`, `_to_delete`, `__pycache__`, `.env*`, `workspace/outputs`의 추적 안 된 산출물(단, acceptance source artifact 9개는 넣음). `.git` 포함. 두 사본의 차이는 아래 적용 파일뿐(diff 확인).
- `sim`에만 적용: ① `Claude outputs/kiwoom-repin-2026-10-07/repin_apply.py`로 포인터 17곳 교체 ② `migrate_integrated_shadow_cohort.py --reason SESSION_AWARE_KIWOOM_PROVIDER_AUTHORITY_CHANGE`.
- 테스트 Python: 3.13.15 + requirements.txt(yfinance 1.7.0 → pandas 3.0.6) + pydantic 2.13.5.

| 확인 | base(활성화 전) | sim(①② 적용) |
|---|---|---|
| 운영 검증기, 45cf manifest | FAIL: drift 2(bridge, pin scope) | FAIL: 포인터 불일치 17(음성 대조) |
| 운영 검증기, 835d manifest | FAIL: 포인터 불일치 | **PASS** |
| `test_v2_6_7_session_aware_kiwoom_priority` (42) | failures 2 | **OK** |
| `test_materialize_…_candidate` (26) | OK | OK |
| `test_kiwoom_token_reuse` 15 / `test_migrate_integrated_shadow_cohort` 3 / `test_scheduled_input_gate` 8 | OK | OK |
| `validate_schema_contracts.py` | PASS | PASS |
| 전체(99 파일, Ran 2492) | failures 137, errors 13 | failures 135, errors 13 |
| 새 실패 | — | **0** |
| 해소 | — | v2_6_7 `test_extended_provider_scope_candidate_validates_without_activation`, `test_guarded_priority_requires_locked_acceptance_manifest` |

- materialize 테스트 test_05·test_12는 source artifact가 있으면 통과한다(빌더 보고 7절 "확인 필요" 해소).
- 남은 148건은 두 사본에서 id가 같다(환경 원인: 리눅스, pandas 3, 추적 안 된 산출물 없음). 대부분 `test_portfolio_decision_dashboard`(약 140건). `test_v2_6_integration` int_14(배포 해시)도 공통 실패 — 원인 확인 필요. Windows 전체 스위트 비교는 Judge가 한다.
- 정책 해시(원시 = 정규화, LF만, 크기 불변, JSON 경로 diff 17개, 권한 필드 불변):
  - `kiwoom-session-aware-priority-policy.json` `d315c3d3…` → `2136f53c44f4b87e963af54005bc44b724a5acdfb934ea28dca6be24623d7705`
  - `source_capabilities.json` `351a3495…` → `b6e91a2f3c3f489cb4281ed64c9b91320805130ab155aee86350b635e7062476`
- 새 지문 `2acacfbba4400474…`, 새 cohort `integrated-shadow-2acacfbba4400474`, 보관 `cohorts/integrated-shadow-a0d3e69e9bc23a1b/superseded_progress.json`.
- **주의: VM에서 migrate를 실행하면 `shadow_progress.json`이 LF로 써진다(sim CR 0).** 스크립트가 텍스트 모드로 쓰기 때문이다. 원본에서는 Windows 터미널에서 실행해야 CRLF 28줄이 유지된다(R9 선례). 그래서 9번은 사용자 터미널에서 한다.

## 5. 다음 단계와 승인

1. **Judge(별도 Claude Code 세션):** `kiwoom-repin-judge-prompt-2026-10-07.md`.
2. Judge PASS → 사용자가 후보 파일과 문서 3개(이 보고서, Judge 지시문, Judge 보고)를 경로 지정으로 커밋. 커밋 뒤 `git ls-files --eol`로 후보가 `i/lf w/lf`인지 확인. 후보 파일은 LF를 유지해야 한다(R8 조건 ①; R9 보고 5절에 따르면 Windows git은 `core.autocrlf=true`).
3. **8번 활성화(Cowork, 사용자 명시 승인 필요):** 원본에서 `repin_apply.py` 먼저 확인 모드, 그다음 `--apply`. 직전에 2절 사전 확인을 다시 한다.
4. **9번 cohort 이전(사용자 Windows 터미널, 승인 필요), 8번 직후 바로:** `python manage-us-stock-strategy/scripts/migrate_integrated_shadow_cohort.py --reason SESSION_AWARE_KIWOOM_PROVIDER_AUTHORITY_CHANGE`. 8~9 사이에 shadow 기록이 돌면 새 cohort의 `observed_attempts`가 1이 되어 이관이 `CURRENT_SEMANTIC_COHORT_NOT_ZERO`로 멈춘다(fail-closed, 이전 카운터 0이라 손실 없음, 보관 파일만 안 생김). Judge가 바로잡은 내용(8절).
5. 10번 확인(Cowork): 운영 검증기 835d PASS, 대상 테스트, 스키마 감사, `shadow_progress.json` CRLF 28줄.
6. 11번 사용자 커밋(경로 지정: 정책 2개, `shadow_progress.json`, 새 보관 파일, 문서).
7. 빌더 보고 9절 실측 검증(사용자 PC) 통과 → `portfolio-exposure-review.md`의 "Pending change" 문단을 확정 문장으로 바꾼다(K0). 이 파일이 스킬 배포 해시 대상인지 먼저 확인.

## 6. 확인 필요

- Windows Python에서 같은 입력이 같은 후보 바이트를 내는지(Judge 2번).
- Windows 전체 스위트 base vs sim(Judge 5번).
- `scheduled_input_gate.py` 배포 출처 검사(`CURRENT_PROVIDER_SCOPE_HASH_MISMATCH`·`CURRENT_SEMANTIC_COHORT_MISMATCH`)가 예약 런타임 clone 경로에서 활성화 뒤 어떻게 되는지. 그 경로는 보류 중(r-sched-b). `test_scheduled_input_gate`는 sim에서 통과.
- `test_v2_6_integration` int_14 공통 실패 원인.

## 7. 남긴 파일

- 원본 폴더: 후보 1개(새 폴더), 이 보고서, Judge 지시문, `Claude outputs/kiwoom-repin-2026-10-07/repin_apply.py`(적용 도구 v2, sha256 `9742aa45…`, 커밋 대상 아님). Judge가 본 v1(`67152f53…`)은 같은 폴더에 `repin_apply_v1_judge-reviewed.py.txt`로 보관.
- 사본·테스트 로그는 VM 홈에만 있다(세션이 끝나면 사라짐). 원본의 다른 파일은 바꾸지 않았다.

## 8. Judge 결과와 조건 처리 (2026-10-07)

판정 **PASS-WITH-CONDITIONS** (별도 Claude Code 세션, Windows Python 3.13.15, 원문 `kiwoom-repin-judge-report-2026-10-07.md`).
Judge가 직접 확인한 것: Windows에서 같은 입력으로 같은 후보 바이트(sha `835d4f46…`) 재현, 내용·권한 필드 일치, Windows 사본 모의에서 새 실패 0·v2_6_7 2건 해소(전체 2521건), Windows migrate 뒤 `shadow_progress.json` CRLF 28 유지, 보관 파일 CRLF 36.

| 발견 | 처리 |
|---|---|
| 1 [M] 적용 도구 검사가 assert라 `-O`/`PYTHONOPTIMIZE`에서 사라짐 | **고침(v2).** assert를 모두 명시 검사(종료 코드 2)로 바꿈, `-O`면 시작 즉시 종료, old·new를 `[0-9a-f]{64}`로 검사 |
| 2 [L] 두 번째 파일 재확인이 첫 파일 쓴 뒤, 쓰기 비원자적 | **고침(v2).** 쓰기 전에 두 파일 모두 재확인, 파일마다 임시 파일 + `os.replace`, 두 번째 쓰기 실패 시 첫 파일을 원래 바이트로 복구 |
| 3 [L] 대소문자 섞인 해시 미집계, 바뀐 경로는 개수만 단언 | Judge는 수용. v2에서 보강: 대소문자 무시 개수 = 소문자 + 대문자 검사, 바뀐 경로를 정확한 집합(acceptance_evidence 1 + provider_scopes[0..14] 15 + kiwoom_rest 행 1)으로 검사, 각 경로의 이전·새 값 확인 |
| 4 [L] migrate가 OS 줄바꿈으로 씀 | 계획대로 9번은 Windows Python에서 실행하고 실행 뒤 CRLF 28 확인 |
| 5 [L] 9번 결과 확인 | 10번에서 `COHORT_SUPERSEDED_AND_ZERO_INITIALIZED`, 보관 파일, `test_provider_authority_change_starts_zero_count_cohort` 통과 확인 |
| 6 [L] autocrlf에서 후보 LF 유지 | 커밋 뒤 `git ls-files --eol`로 `i/lf w/lf` 확인. `.gitattributes`(`workspace/research/provider-evidence/kiwoom/** -text`)는 만들지 않음 — 별도 K2/K3 후보 |
| 위험 (a) 전제 수정 | 위 5절 4번에 반영(`CURRENT_SEMANTIC_COHORT_NOT_ZERO`로 멈춤, `shadow_acceptance.py` `apply_attempt`·record 경로 확인) |

v2 시험(VM, 원본과 같은 정책 2개의 사본, 원본 쓰기 없음):
1. 확인 모드 → 17, 파일 불변 / 2. `--apply` → APPLIED 17, 결과 바이트가 v1 sim 결과와 같음, 임시 파일 남지 않음 / 3. 재적용 → 거부(old 0곳) / 4. `-O` + 틀린 old + `zz` → 시작 즉시 거부, 불변 / 5. `PYTHONOPTIMIZE=1` → 거부, 불변 / 6. new `zz` → 거부 / 7. 틀린 old(16진 64자) → 거부 / 8. 소문자 하나를 대소문자 섞음 → 거부 / 8b. 대소문자 섞인 해시 추가 → "mixed-case" 거부 / 9. 포인터 하나를 다른 필드로 옮겨 개수 유지 → "changed paths differ" 거부 / 10. 두 번째 `os.replace` 실패 주입 → 첫 파일 복구, 두 파일 모두 원래 바이트, 임시 파일 없음.

Judge가 "확인 필요"로 남긴 것: 저장소 밖 Cowork 예약이 shadow 기록을 하는지, dashboard 공통 실패 69건 원인. VM의 `PYTHONOPTIMIZE`는 비어 있음(확인함, v2에서는 무관).
