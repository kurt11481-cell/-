# I0 Builder 보고서: 브로커 조정 루프 (2026-09-30)

- 역할: I0 Builder (K3). 지시문: `docs/claude/system-review-p4-roadmap-2026-09-30.md` 부록 A1.
- 설계: P3 §2·§4·§10-2, P4 §1(1-2~1-12)·§4 S1·S3·§8.
- 작업 위치: worktree `.claude/worktrees/i0-reconcile`, 브랜치 `worktree-i0-reconcile`, 기준 커밋 `6a5a167`.
- 이 문서에는 보유 수량, 현금, 계좌 정보가 없다. 실데이터 결과는 상태 코드와 경고 코드만 적는다.

---

## 0. 결론

1. **조정 루프를 만들었다.** 구성은 다음 두 명령이다.
   - `reconcile_broker_state.py propose`: 조회 전용. 상태 파일을 쓰지 않는다.
   - `reconcile_broker_state.py apply --confirm <코드>`: 사용자 확인 코드가 있어야 적용한다.
   - 쓰기 경로는 `apply_user_confirmed_broker_snapshot.apply_confirmed` 하나다.
2. **안전 검사를 라이브러리 안에 넣었다.** 라이브러리를 직접 불러도 적용되지 않는 경우는 다음과 같다.
   - unresolved 항목이 남음(스크린샷 경로 포함)
   - 만료, 상태 해시 불일치, revision 불일치
   - 제안 내용 변조, 코드 없음, 코드 불일치
   - 원장과 상태 불일치
3. **실데이터 제안 1회가 첫 시도에 성공했다.**
   - 필수 조회 3개가 PASS, 제안 스키마 PASS.
   - 상태 파일 sha256이 실행 전후 같다.
   - 적용 후 알림 엔진 검사 PASS. 경고는 `OPEN_ORDERS_UNVERIFIED` 하나다.
4. **테스트는 기준선 대비 새 실패가 0이다.**
   - 대상 테스트 8개 모듈과 신규 `test_reconcile_broker_state.py`(48건)로 확인했다.
   - 전체 테스트는 1,916건 중 실패 314건으로 기준선 목록과 같다(§3-2).
   - 스키마 감사 PASS. 고정 파일 16개와 정책 파일의 diff는 비어 있다.
5. **Judge가 봐야 할 판단 두 가지**
   - 미체결 확인 없이 적용(10번): 16회 모두 실패였던 미체결 조회에 더해, 실현손익 조회도 16회 모두 실패였다. 이번 변경 전부터 그랬다(§6).
   - "값은 같고 확인 기록만 오래된" 경우의 제안: P3 원안에서 바뀐 점이며, 사용자가 결정했다(§1).

---

## 1. 이번 세션의 사용자 결정

| 결정 | 내용 |
|---|---|
| 2단계 조회 승인 | 잔고·예수금·체결 조회 전용 호출 1회씩. 출력은 키 이름과 `return_code`만 |
| 계획 승인 | §2 파일 변경, §4 기존 테스트 4건 변경 |
| 값 일치 + 확인 기록이 오래됨 | **확인 기록만 갱신하는 제안(`change_kind=METADATA_ONLY`)을 만든다.** P3 §4-1 3단계("일치하면 끝")를 바꾼 것이다. 이유는 두 가지다. ① 알림 엔진은 브로커 확인 `as_of`가 4일을 넘으면 `STATE_MISMATCH`로 멈춘다. ② P4 §7의 상태 나이 목표는 "최근 분석일과 같음"이다. 날짜가 같고 기록도 같으면 `NO_CHANGE_REQUIRED`다 |
| 원장 밖 상태 변경 | **경고를 붙이고 적용을 거부한다.** 제안에 `STATE_CHANGED_OUTSIDE_LEDGER`를 경고와 unresolved 둘 다에 넣는다. 라이브러리도 적용 시점에 원장을 다시 확인해 거부한다(P4 §1-12 손상 정의, §5 "적용 중지") |
| 수동 분석 명령 | 인자 없는 기본 실행: `python manage-us-stock-strategy/scripts/run_manual_portfolio_analysis.py` |

## 2. 변경 파일

| 파일 | K | 내용 |
|---|---|---|
| `scripts/kiwoom_account_readonly_bridge.py` | K3 | `_account_return_code_ok`(:78)는 필드가 있고 값이 int 0 또는 "0"일 때만 성공으로 본다. `False`, `0.0`, `"0000"`, 누락은 실패다. `_fetch_account_page`(:109)가 이 함수를 쓴다. 고정 파일 `kiwoom_runtime_bridge._return_code_ok`는 import만 뺐다(파일 불변) |
| `scripts/kiwoom_broker_shadow.py` | K3 | `normalize_snapshot`은 불변이다. 다음을 추가했다: I0 입력 검증 `validate_reconciliation_inputs`(:169), 파생 원가(:239), 제안 해시(:244), 통일 형식 `reconciliation_proposal`(:300). 새 local import는 없다(표준 라이브러리만) |
| `scripts/run_kiwoom_broker_shadow.py` | K3 | `collect_broker_snapshot()`과 `repo_relative()`로 분리했다. 기존 CLI는 유지한다. 알림 엔진 검사가 없으므로 기존 CLI가 만든 제안은 `POST_APPLY_CHECK_NOT_RUN`으로 BLOCKED다 |
| `scripts/apply_user_confirmed_broker_snapshot.py` | K3 | 라이브러리 검사, 백업, 원장, `last_updated_at`, 줄바꿈 유지, 쓰기 후 재검증을 넣었다(§8) |
| `scripts/reconcile_broker_state.py` (신규) | K3 | `propose` / `show` / `apply` CLI |
| `schemas/kiwoom-reconciliation-proposal.schema.json` (신규) | K3 | 키움 제안 스키마 (`additionalProperties: false`) |
| `assets/locales/reconcile-broker-state-ko-KR.json` (신규) | K1 | 한국어 문구. `scripts/*.py`는 ASCII만 허용되고(`test_language_contract`), `ko-KR.json`은 정책 해시로 고정돼 있다 |
| `.gitignore` | K3 묶음 | `stock-strategy-system/backups/`, `stock-strategy-system/reconciliation_ledger.jsonl`, `workspace/outputs/reconciliation/` |
| `CLAUDE.md`(:7-13), `AGENTS.md`(:35) | K3 묶음 | "snapshot **AND** 사용자 확인" 문구와 apply 실행 규칙 |
| `.claude/settings.json`(:14-18) | K3 묶음 | deny: `Bash(*reconcile_broker_state.py apply*)`, `PowerShell(…)`, `Edit(/stock-strategy-system/portfolio_state.json)`, 원장, 백업 |
| `references/broker-snapshot-reconciliation.md`(:57-) | K1 | ① Windows 명령 블록 ② Cowork 확인 절차 ③ 터미널 대체 경로 |
| `tests/test_reconcile_broker_state.py` (신규) | K2 | 48건 |
| `tests/test_kiwoom_broker_shadow.py`, `test_v2_5_broker_snapshot.py`, `test_v2_6_broker_beginner.py` | K2 | 기존 테스트 4건 변경(§4) |

**건드리지 않은 것**
- `run_manual_portfolio_analysis.py`
- `kiwoom_runtime_bridge.py`와 나머지 고정 파일 16개
- 정책 파일: `alert_policy.json`, `workspace/policies/*`
- 원본 폴더의 상태 파일
- 스크린샷 스키마(2.5)
- **`SKILL.md`(되돌림)**
  - 처음에는 라우팅 줄과 130행 문구를 고쳤다.
  - 그런데 `SKILL.md`는 승인 정책 `alert_policy.json`의 배포 게이트가 sha256으로 고정한 파일이다(`required_source_skill_sha256`, `validate_skill_deployment.ARTIFACTS`).
  - 1차 전체 테스트에서 새 실패 3건이 나왔다(`test_v2_4_automation` 2건, `test_v2_6_integration::test_int_14`).
  - 그래서 수정을 되돌렸다. 기존 라우팅 줄("holdings/cash reconciliation → broker-snapshot-reconciliation.md")이 이미 절차 문서를 가리킨다.
  - 130행의 옛 문구("explicit user confirmation or a verified read-only broker snapshot")는 그대로 남았다(§11).

## 3. 테스트 (기준선 대비)

### 3-1. 대상 테스트 (A1 1단계 목록 + 신규·관련)

| 모듈 | 기준선 | 변경 후 |
|---|---|---|
| test_kiwoom_broker_shadow | 24 OK | 24 OK |
| test_v2_5_broker_snapshot | 27 OK | 27 OK |
| test_v2_6_broker_beginner | 25 OK | 25 OK |
| test_manual_portfolio_analysis | 115, ERROR 3 | 115, ERROR 3 (같은 3건) |
| test_k2_evidence_contract | 34 OK | 34 OK |
| test_k2_bridge_evidence_integrity | 17 OK | 17 OK |
| test_v2_6_4_kiwoom_adapter | 44 OK | 44 OK |
| test_broker_visibility_audit | 3 OK | 3 OK |
| test_reconcile_broker_state (신규) | 없음 | 48 OK |
| test_k2_continuation_coherence (계좌 bridge 사용) | 13 OK | 13 OK |
| test_language_contract (ASCII) | 2 OK | 2 OK |

- `test_manual_portfolio_analysis`의 ERROR 3건은 기준선과 같다: `ScheduledRegisteredTaskBindingTests`의 `test_canonical_path_does_not_promote_grade_b`, `test_t1_…`, `test_t8_…`.
- 원인은 worktree 체크아웃 줄바꿈 때문에 원시 해시 증거가 달라져 나는 `INTEGRITY_FAILURE`다(`kiwoom-acceptance-pin-diagnosis` 진행 기록과 같은 부류).
- test_04와 test_08은 통과했다.

### 3-2. 전체 테스트 (서브에이전트, 1회씩)

| 실행 | 테스트 수 | 결과 | 실패 항목 | 기준선 대비 |
|---|---|---|---|---|
| 기준선(변경 전) | 1,868 | FAILED (failures=23, errors=291, skipped=1) | 314 | - |
| 1차(변경 후) | 1,916 | FAILED (failures=26, errors=291, skipped=1) | 317 | 새 실패 3건(`SKILL.md` 배포 게이트 해시, §2) |
| 2차(`SKILL.md` 되돌린 뒤) | 1,916 | FAILED (failures=23, errors=291, skipped=1) | 314 | **새 실패 0, 해소 0** |

- 늘어난 48건은 신규 `test_reconcile_broker_state.py`다.
- 기준선 실패 314건의 대부분은 worktree 체크아웃 줄바꿈 때문에 원시 해시 증거가 달라져 생긴다. `test_portfolio_decision_dashboard` 188건, `test_integrated_authority_snapshot` 38건 등이다.
- 알려진 acceptance 실패 17건과 Windows 전용 실패 6건도 기준선에 포함돼 있다.

### 3-3. 기타 검증

- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`: PASS.
- 고정 파일 16개(`kiwoom-acceptance-pin-diagnosis-2026-09-29.md` §2-1)와 정책 파일(`stock-strategy-system/alert_policy.json`, `workspace/policies/`)은 `git diff HEAD`가 비어 있다.
- `normalize_snapshot` 본문(정의부터 `return snapshot`까지)은 기준 커밋과 바이트 단위로 같다(CR 제거 후 sha256 앞 16자리 `b69bc42e2e408c53` 일치).
- 기존 파일의 줄바꿈(CRLF)은 모두 유지했다. 새 파일 4개는 LF이며, git이 커밋할 때 정규화한다.

## 4. 기존 테스트 변경표 (이전 기대 → 새 기대)

| 테스트 | 이전 기대 | 새 기대 | 약화 여부 |
|---|---|---|---|
| `test_kiwoom_broker_shadow::test_no_fill_inference_or_auto_apply` | `reconciliation_proposal(…, expected_before_hash=원시 파일 해시)` 호출. `auto_apply`와 `fill_inference_performed`가 False, 파일 해시 불변 | 새 시그니처(`results`, `maximum_age_seconds`). 같은 단언에 `expected_portfolio_hash_before == canonical_hash(state)`를 추가 | 아니오(단언 추가) |
| `…::test_state_revision_is_bound` | `current_state_revision == state_revision`, status `USER_CONFIRMATION_REQUIRED` | `expected_state_revision == state_revision`, 같은 status. 알림 엔진 검사가 없으면 BLOCKED이므로 테스트용 검사 함수(PASS)를 넘김 | 아니오(필드 이름 통일, P4 §1-4) |
| `test_v2_5_broker_snapshot::test_v25_bs_05_confirmed_proposal_atomic_apply` | unresolved 3개(캡처일·보유 완결·통화 확인)가 남은 제안이 적용됨 | 같은 픽스처에서 세 확인 항목을 VERIFIED로 둔 입력의 제안(unresolved 0)이 적용됨. unresolved가 0인지 단언을 추가하고 기존 단언은 모두 유지. 백업·원장은 임시 폴더에 씀 | 아니오. 라이브러리가 더 엄격해졌다(P3 §4-4). 기존 입력이 거부되는지는 신규 `test_screenshot_proposal_with_unresolved_fields_rejected`가 단언 |
| `test_v2_6_broker_beginner::test_bs_03_explicit_confirmation_atomic_apply_only` | 위와 같음 | 위와 같음 | 아니오 |

오류 코드를 단언하는 기존 테스트(`test_v25_bs_06`, `06a`, `26`, `test_bs_04`)는 바꾸지 않았다. 이를 위해 라이브러리의 기존 검사 순서를 유지하고 새 검사를 그 뒤에 두었다. 모든 검사는 쓰기보다 앞에 있다.

**Judge FAIL 수정(§12)에서 바뀐 기대.** "이전 기대"는 커밋 `dfb7f7b` 기준이다.

| 테스트 | 이전 기대 | 새 기대 | 약화 여부 |
|---|---|---|---|
| `test_v2_5_broker_snapshot::test_v25_bs_05_confirmed_proposal_atomic_apply` (F1) | 세 확인 항목을 VERIFIED로 둔 2.5 제안(unresolved 0)이 적용됨. revision 2, 보유, source 기록, 해시 변화 | 같은 제안·확인이 `SCREENSHOT_PROPOSAL_APPLY_NOT_SUPPORTED`로 거부됨. unresolved 0 단언은 유지. 상태 바이트 불변, 폴더 파일 목록 불변(백업·원장·감사 파일 없음). **적용 원자성 검증은 키움 경로 테스트가 맡는다:** `LibraryApplyTests.test_apply_writes_only_reconciled_fields_with_backup_and_ledger`, `test_lf_state_stays_lf_and_ledger_chains_across_applies`, `CliTests.test_apply_with_the_users_code`. 추적을 위해 테스트 이름은 유지 | 아니오. 사용자 결정 F1로 적용 대상이 줄었다. 원자적 적용 단언은 키움 경로에 그대로 있다 |
| `test_v2_6_broker_beginner::test_bs_03_explicit_confirmation_atomic_apply_only` (F1) | 위와 같음(revision 2) | 위와 같음 | 아니오(위와 같음) |
| `test_reconcile_broker_state::test_screenshot_path_with_resolved_fields_still_applies` → `…_is_rejected_in_v1` (F1) | 적용됨. `last_updated_at`이 호출자가 준 `confirmed_at`, 원장 1줄 | 거부됨. `assert_nothing_written`(상태 바이트, 백업, 원장, 감사 파일)으로 단언 | 아니오. F1. 호출자 `confirmed_at` 사용은 F2로도 없어졌다 |
| `…::test_state_changed_outside_ledger_blocks` (17번) | 원장 after ≠ 현재 상태 → BLOCKED, 경고와 unresolved 둘 다 | 원장 마지막 줄 before = 현재 상태 → BLOCKED, 경고와 unresolved, patch `{}`, 표에 중단 문구. 그 밖의 after ≠ 현재 → `USER_CONFIRMATION_REQUIRED`, 경고만(unresolved 아님), 스키마 PASS, 표에 주의 문구와 확인 코드. after = 현재 → 경고 없음. 원장 무결성 실패 단언은 유지 | 아니오. 사용자 결정(17번)으로 차단 범위가 좁아졌다. 차단 사례 단언은 남기고 경고 사례 단언을 더했다 |
| `…::test_ledger_mismatch_or_broken_chain_rejected` (17번) | before 없는 원장 줄(after=`f…`)과 경고 없는 제안 → `STATE_CHANGED_OUTSIDE_LEDGER`. 체인 깨짐 → `LEDGER_INTEGRITY_FAILED` | 원장 before = 현재 → 경고 없는 제안과 unresolved를 지운 위조 제안 모두 `STATE_CHANGED_OUTSIDE_LEDGER: STATE_EQUALS_LAST_LEDGER_BEFORE_HASH`. 그 밖의 원장 밖 변경과 경고 없는 제안 → `OUTSIDE_LEDGER_WARNING_NOT_IN_PROPOSAL`. 체인 깨짐 단언 유지. 감사 파일 없음 단언 추가 | 아니오. 이전 입력(경고 없는 제안)은 여전히 거부된다. 오류 코드만 바뀌었다 |
| `…::test_path_aliases_and_protected_names_rejected` (F3) | `ledger_path=상태 경로` → `BROKER_APPLY_PATH_ALIAS_REJECTED` | 인자가 없어졌으므로 `audit_path=상태 경로`와 "원장 파일 이름을 가진 상태 경로"(파생 원장 = 상태) 두 경우를 같은 코드로 거부. 보호 이름 단언 유지 | 아니오. F3으로 인자가 없어졌다. 인자 자체가 거부되는지는 신규 테스트가 단언 |

## 5. `return_code` 확인 결과 (A1 2단계)

- **방법**
  - 저장소 밖 임시 스크립트로 런타임 venv에서 `_fetch_account_page`를 불렀다.
  - 조회 3개를 첫 페이지만 1회씩 불렀다.
  - 출력은 최상위 키 이름과 `return_code`만이다.
  - 실행 전에 사용자 승인을 받았다.
- **결과:** 정상 응답 3개 모두 `return_code`가 있고 값은 `0`(int)이다. 멈춤 조건에 해당하지 않는다.
  - 잔고 `ust21070`: 최상위 키에 `return_code`, `return_msg`, `result_list`와 합계 필드가 있다.
  - 예수금 `ust21110`: `return_code`, `return_msg`, `result_list`, 원화 관련 필드
  - 체결 `ust21510`: `return_code`, `return_msg`, `result_list`

## 6. 실데이터 제안 1회 (A1 6단계, 읽기 전용)

- **명령:** `python manage-us-stock-strategy/scripts/reconcile_broker_state.py propose`
  - 기본값 사용: worktree 상태 파일 복사본, 공식 런타임, `workspace/outputs/reconciliation/`
  - apply는 실행하지 않았다.
- **첫 시도에 성공했다(재시도 0회).**
  - 필수 조회 PASS: 잔고, 예수금, 체결
  - 표시 전용 조회: 예수금 상세 PASS, 미체결과 실현손익 `KIWOOM_API_RESPONSE_ERROR`
- **제안 결과**
  - 스키마 PASS, status `USER_CONFIRMATION_REQUIRED`, change_kind `VALUES`
  - 바뀌는 항목(이름만): 보유 수량 1종목, 파생 원가, 원가 총합, 가용 현금, 브로커 확인 기록
  - 경고는 `OPEN_ORDERS_UNVERIFIED` 하나, unresolved는 없음
  - 적용 후 알림 엔진 검사(`evaluate_alerts.leveraged_state_integrity_errors`) PASS, 정책 종목 불일치 없음. P4 S4의 예상("NBIS 수량만 다르면 통과")과 같다.
  - 제안 안의 경로는 저장소 상대경로다: `stock-strategy-system/portfolio_state.json`, `workspace/outputs/reconciliation/<UTC>/…`
  - `order_authority=false`, `inferred_fills=false`
- **상태 파일 sha256:** 실행 전후 같다(`017225ec…`, 원본 폴더 파일과도 같다).
- **원가 교차검증(표시 전용):** 파생 원가와 `evlt_amt − pl_amt`가 1달러 넘게 다르다(`DIFFERS`).
  - `evlt_amt`가 원화이거나 `frgn_stk_book_uv`에 수수료가 포함됐을 가능성이 있다. 확인 필요 항목으로 남긴다.
  - 적용 판단에는 쓰지 않는다.
- **실현손익 조회 실패의 원인은 이번 변경이 아니다.** 과거 수동 분석 결과 20개(원본 폴더, 읽기만)를 집계했다.
  - 배치가 성공한 16회 모두 미체결과 실현손익이 `KIWOOM_API_RESPONSE_ERROR`였다.
  - 예전 검사에서도 이 값은 `return_code`가 있고 0이 아닐 때만 난다.
  - S1b 진단에 실현손익(ust21630)도 함께 넘긴다.

## 7. Judge 확인 항목별 근거

| # | 항목 | 근거 |
|---|---|---|
| 1 | 라이브러리 직접 호출에서 unresolved·만료·해시 불일치 제안이 적용되지 않음 | `apply_user_confirmed_broker_snapshot.py:233-265`, `LibraryRejectionTests`(`test_unresolved_fields_rejected_even_with_valid_identity`, `test_screenshot_proposal_with_unresolved_fields_rejected`, `test_expired_proposal_rejected`, `test_state_hash_and_revision_mismatch_rejected`, `test_tampered_proposal_rejected`, `test_caller_schema_cannot_relax_the_pinned_schema`). 거부될 때 상태 바이트 불변, 백업·원장·감사 파일 없음(`assert_nothing_written`) |
| 2 | CLI는 코드 없음·불일치·다른 제안 코드에서 적용하지 않음. 확인 기록에 방법·시각·문구가 남음. 규칙·권한 거부 적용 | CLI `reconcile_broker_state.py:287-288`(argparse 필수), 라이브러리 `:250-259`. 테스트: `CliTests.test_apply_requires_the_code`, `test_apply_rejects_wrong_or_foreign_codes_and_missing_messages`, `LibraryRejectionTests.test_confirm_code_missing_wrong_or_from_another_proposal_rejected`. 기록: 원장 줄의 `confirmation_method`, `confirmed_at`, `user_message`, 상태의 `last_confirmed_broker_snapshot.confirmation_method`(`test_apply_with_the_users_code`). 규칙: `CLAUDE.md:7-13`, `AGENTS.md:35`, `.claude/settings.json:14-18`(`RepositoryRuleTests`) |
| 3 | `never_touched` 항목이 적용 전후 바이트 수준으로 같음 | `_assert_untouched`(`apply…:193`)가 쓰기 전에 검사한다. 대상은 쓰기 대상 9개를 뺀 모든 최상위 필드다. `LibraryApplyTests.test_apply_writes_only_reconciled_fields_with_backup_and_ledger`(canonical JSON 비교), `test_untouched_guard_detects_other_field_changes` |
| 4 | 체결 추론·주문 경로 없음 | 계좌 API는 `/api/us/acnt` 조회 6개뿐이고 주문 단어가 없다(`AccountReturnCodeTests.test_account_routes_are_read_only`). 제안의 `order_authority=false`, `inferred_fills=false`, `fill_inference_performed=false`는 스키마 const다. 원장 `inferred_fills=false`, 조정 기록 `trade_id=null`, `fill_recorded=false` |
| 5 | 필수 조회 실패, `return_code` 누락, 음수·소수 수량, 900초 초과가 FAIL | `kiwoom_broker_shadow.py:169-236`, `kiwoom_account_readonly_bridge.py:78-86`. `InputValidationTests` 전체, `AccountReturnCodeTests` |
| 6 | `normalize_snapshot` 계약 불변, 수동 분석 변화는 fail-closed뿐 | 본문이 바이트 단위로 같다(§3-3). 키 집합 단언은 `test_valid_inputs_have_no_errors_and_normalize_contract_is_unchanged`. 수동 분석에 미치는 변화는 계좌 조회 `return_code` 엄격화 하나다. 이번 실데이터에서 새로 실패한 조회는 없다(§6) |
| 7 | 백업·원장이 쓰기보다 먼저, git 제외 | 순서: 백업 `:279` → 원자료 재확인 `:280` → 원장 `:297` → 원자적 교체 `:298` → 재검증 `:299`. `.gitignore:45-48`, `test_state_backups_ledger_and_outputs_are_git_ignored`(`git check-ignore`) |
| 8 | 분석 경로 import 금지 | `test_manual_portfolio_analysis` test_08 통과. 추가로 `BoundaryTests.test_analysis_path_never_reaches_the_apply_modules`가 `run_manual`의 local import를 이행적으로 따라가며 적용 모듈이 없음을 확인한다 |
| 9 | 적용 후 알림 엔진 검사 결과가 표에 보임 | `reconcile_broker_state.py:59-78`(패치한 복사본에 검사 실행), 표 렌더링 `:146-152`. 테스트: `test_warnings_and_post_apply_check_are_recorded`(실패 이유가 표에 나옴), `test_real_alert_engine_check_runs_on_a_patched_copy`(실제 정책) |
| 10 | 미체결 확인 불가를 "경고 후 적용 허용"으로 한 결정, 현금 의미 라벨 | 아래 §7-1 |
| 11 | 제안 안의 경로가 저장소 상대경로 | `run_kiwoom_broker_shadow.repo_relative`, `test_paths_are_repository_relative`, 실데이터 제안(§6) |
| 12 | canonical 해시와 필드 이름 통일 | 제안: `expected_portfolio_hash_before = canonical_hash(state)`, `expected_state_revision`, `bundle_id`, `scope`, `proposed_patch`. 적용: 같은 이름으로 비교(`apply…:233-235`). `test_unified_format_and_identity`(옛 필드 없음) |
| 13 | 커밋 파일에 보유 수량·현금·계좌 정보 없음 | 테스트 값은 합성(TEST_ONLY, AAA/BBB)이다. 이 보고서에는 코드만 있다. 실데이터 제안 파일은 git 제외 폴더에만 있다. 커밋 전 `git status`로 확인한다(§10) |
| 14 | 규칙 문구 | `CLAUDE.md:7-13`, `AGENTS.md:35`, 절차 문서 `references/broker-snapshot-reconciliation.md` §2 5번(이번 대화의 "확인 <코드>"만, 코드 입력 금지, 재사용 금지, 예약 작업 금지). `test_agent_rules_require_snapshot_and_user_confirmation`, `test_cowork_procedure_documents_the_confirmation_rules` |
| 15 | 기존 테스트 변경이 기대를 약하게 하지 않음 | §4 |

### 7-1. 10번에 대한 Builder 의견 (Judge 판단 대상)

- **미체결 확인 불가인데 적용을 허용하는 근거**
  - 보유 수량은 `poss_qty`(held)라 미체결 주문과 무관하게 현재 보유분이다.
  - 제안과 상태에 `open_orders_verified=false`가 남는다.
  - 표에 경고가 보인다.
- **남는 위험:** 체결 대기 중인 매수·매도가 있으면 가용 현금과 다음 날 보유가 곧 바뀐다. 이 경우 다음 제안에서 다시 조정된다.
- **실데이터 사실:** 미체결뿐 아니라 실현손익 조회도 과거 16회 모두 실패였다(§6). S1b 결과를 반영해 판단해 달라.
- **현금 라벨**
  - `available_cash_usd` = min(출금가능, 주문가능) USD이고 `cash_verified_scope=available_cash_only`다.
  - 제안의 `cash_semantics`에 `settled_cash=false`, `unsettled_funds_included=false`, `margin_or_credit_included=false`를 적었다.
  - 이 값은 `portfolio_policy_gates.py`가 허용하는 범위다.

## 8. 설계 결정 (A1 4a~4j)

- **만료 검사 적용 범위(4a)**
  - 키움 제안은 필수다(스키마 required, 라이브러리가 `expires_at` 검사).
  - 스크린샷 제안(2.5)에는 해당 필드가 없어서 적용하지 않는다. 대신 unresolved 검사는 두 경로 모두에 적용한다.
  - 제안 종류는 `schema_version`으로 나눈다. 모르는 값은 거부한다.
  - 라이브러리는 호출자가 준 스키마와 별도로 자기 고정 스키마로 검증한다. 느슨한 스키마를 넘겨도 우회되지 않는다.
- **만료 시각:** 필수 조회 중 가장 이른 시각 + 정책 `maximum_age_seconds`(900초). 입력 검증도 같은 시각을 기준으로 900초 초과를 FAIL로 본다.
- **`confirm_code`**
  - `proposal_id`(64자리)는 두 식별자를 뺀 제안 전체의 canonical 해시다. 코드는 그 앞 8자리 대문자다.
  - 라이브러리가 해시를 다시 계산하므로 제안을 고치면 적용되지 않는다.
  - 고친 뒤 해시를 다시 만들면 코드가 바뀌어, 사용자가 본 코드와 맞지 않는다.
- **`as_of`**
  - 필수 조회 중 가장 이른 시각의 미국 동부 날짜다(알림 엔진은 미국 세션 날짜와 비교한다).
  - 정확한 시각은 `as_of_timestamp`에 둔다.
  - 이 값과 `holdings_complete`, 현금 범위는 제안에서 가져오고 호출자 값은 쓰지 않는다(키움 경로).
- **줄바꿈(4d):** 상태 파일은 원래 줄바꿈을 유지하고 다시 쓴다. 현재 CRLF라서 VM에서 적용해도 CRLF가 유지된다. 원장(jsonl)은 LF다.
  - 판정은 canonical 해시라 줄바꿈과 무관하다.
  - 상태 파일을 원시 바이트 해시로 읽는 코드는 아래 두 종류다.
    - 한 실행 안의 불변 확인(전후 비교, 적용과 무관): `run_kiwoom_broker_shadow`, `run_broker_visibility_audit`, `run_kiwoom_candidate_discovery`, `audit_holding_baseline_observations`, `activate_mvll_v3_shadow`, `build_nbis_v3_shadow_activation`
    - 실행 사이 비교나 기록: `runtime_contract_suite.py:113`(manifest의 `portfolio_hash`와 비교), `judge_*`(기대 해시와 비교), `run_manual`·`point_in_time_context`·`holding_baseline_operationalization`·`build_strategy_evolution_state`·`run_kiwoom_candidate_primary_replay`·`current_event_risk`·`build_kiwoom_market_snapshot`(기록)
  - 실행 사이 비교는 적용하면 줄바꿈과 상관없이 값이 바뀐다. 특히 `runtime_contract_suite`의 `portfolio_read_only_accessible`은 첫 적용 뒤 manifest가 갱신되기 전까지 false가 된다(확인 필요, 범위 밖).
- **원장 줄 형식:** `previous_entry_sha256`(이전 줄 원시 바이트 sha256, 첫 줄은 0×64), 적용 전후 canonical 해시, revision, 백업 파일 이름, 변경 목록, 확인 방법·시각·사용자 문구
- **쓰기 실패 때의 동작**
  - 원장을 쓴 뒤 상태 교체가 실패하면, 다음 `propose`와 라이브러리가 `STATE_CHANGED_OUTSIDE_LEDGER`로 적용을 막는다.
  - 멈추는 쪽으로 드러나는 설계다. 복원 절차는 P4 §5 대기 항목이다.
- **상태에 쓰는 것**
  - `proposed_patch` 5개 필드와 `state_revision`+1, `last_updated_at`
  - `last_confirmed_broker_snapshot`: `account_id_masked=null`, `account_identifier_stored=false`, `open_orders_verified`, `confirmation_method`, `proposal_id`
  - `holding_change_reconciliations`에 1건 추가: 종목별 `share_changes`, `trade_id=null`, `fill_recorded=false`. 이 필드를 읽는 코드는 없다(`unreconciled_holding_changes`만 오케스트레이터가 읽는다).
- **보유 목록:** 브로커 행을 그대로 따른다(0주 행 포함). 수동 분석 비교(`compare_broker_and_system`)가 종목 집합 일치를 요구하기 때문이다.
- **스크린샷 경로:** 라이브러리에는 남아 있지만 v1에는 CLI가 없다. 새 규칙("`reconcile_broker_state.py apply`로만")에 따르면, 키움 장애 때의 대체 수단으로 쓰려면 별도 작업이 필요하다.

## 9. Claude Code 권한 거부 규칙과 한계 (4i)

- **추가한 deny**
  - `Bash(*reconcile_broker_state.py apply*)`, `PowerShell(*reconcile_broker_state.py apply*)`
  - `Edit(/stock-strategy-system/portfolio_state.json)`, `Edit(/stock-strategy-system/reconciliation_ledger.jsonl)`, `Edit(/stock-strategy-system/backups/**)`
  - Edit 규칙은 Write 도구에도 적용된다. deny는 기존 ask(`Edit(stock-strategy-system/**)`)보다 우선한다.
- **한계(공식 문서 기준):** 명령 문자열을 맞추는 방식이라 다음 호출은 막지 못한다.
  - `python -c "…apply_confirmed(…)"`처럼 라이브러리를 직접 부르는 경우
  - `sh -c`로 감싼 경우, 변수로 조립한 경우
  - 파일 이름을 바꾸거나 복사한 스크립트를 실행하는 경우
  - Bash와 PowerShell 규칙은 따로 적용된다.
  - Cowork 세션과 Codex에는 이 규칙이 적용되지 않는다.
- **실제 방어선:** 라이브러리 검사와 사용자 코드, 확인 기록, 에이전트 규칙이다. 코드는 제안 파일에 있으므로 사람의 확인을 증명하지 못한다(P4 §0-4, 사용자가 받아들인 절충).

## 10. Judge 참고

- **apply CLI 검증 방법:** 이 deny 규칙 때문에 Judge 세션에서는 `reconcile_broker_state.py apply`를 Bash로 직접 칠 수 없다. 다음 방법으로 확인하면 된다.
  - 테스트 `CliTests`를 돌린다(`cli.main([...])`을 임시 폴더에서 호출).
  - 시스템 임시 폴더의 스크립트에서 `reconcile_broker_state.main([...])`을 부른다.
- **합성 픽스처:** 우회 시도는 임시 복사본과 합성 제안으로 충분하다. 테스트 헬퍼는 `account_results`, `base_state`, `make_proposal`이다.
- **worktree 기준선:** worktree에서 전체 테스트를 돌리면 기준선부터 원시 해시 증거 불일치로 실패가 많다. 새 실패만 비교해야 한다.
- **실데이터 제안 파일:** worktree의 git 제외 폴더 `workspace/outputs/reconciliation/20260929T234230Z/`에 있다. 수치가 들어 있으니 Judge 출력에 옮기지 않는다.

## 11. 남은 확인 필요

- **`SKILL.md:130` 문구 불일치.** "explicit user confirmation or a verified read-only broker snapshot"이 그대로 남아 `CLAUDE.md`·`AGENTS.md`와 다르다.
  - 고치려면 `alert_policy.json` 배포 게이트의 skill 해시를 다시 고정해야 한다(승인 정책 수정, K3, 사용자 승인). 설치 사본(`~/.codex/skills`) 갱신도 필요하다.
  - 그 전까지는 `CLAUDE.md`·`AGENTS.md`와 절차 문서가 우선한다.
- VM(Python 3.10.12)에서의 실행. 코드는 표준 라이브러리만 쓰고, `Z` 접미사는 모두 `+00:00`으로 바꾼 뒤 해석한다. 실제 확인은 S4 4-2에서 한다.
- `frgn_stk_book_uv`의 수수료 포함 여부, `evlt_amt` 통화(교차검증 `DIFFERS`, §6)
- 실현손익(ust21630)이 매번 `KIWOOM_API_RESPONSE_ERROR`인 원인. S1b에 추가한다.
- `runtime_contract_suite`의 `portfolio_hash` 고정이 첫 적용 뒤 예약 경로에 주는 영향(§8)
- 스크린샷 경로의 apply CLI 부재(§8)
- `unreconciled_holding_changes`는 적용 때 건드리지 않는다. 조정 뒤 이 목록을 비울지는 정하지 않았다.
- 보유 수량으로 `poss_qty`(held)를 쓰는 결정(P3 제안)을 유지했다. `qty`(settled)와 다를 때의 표시는 없다.

---

## 12. Judge FAIL 수정 (2026-09-30)

- Judge 판정: **FAIL**, §7의 1번 항목("라이브러리 직접 호출에서 unresolved·만료·해시 불일치 제안이 적용되지 않음").
- 같은 worktree에서 최소 수정만 했다. 기준 커밋은 `dfb7f7b`다.
- 아래 결정은 모두 사용자가 이번 세션에서 승인했다.
- 범위 밖 파일은 바꾸지 않았다. 고정 파일 16개, 정책 파일, `SKILL.md`, 상태 파일의 diff가 비어 있다.

### 12-1. 사용자 결정

| # | 결정 | 막는 우회 |
|---|---|---|
| F1 | v1에서는 스크린샷(2.5) 제안의 적용을 라이브러리 `apply_confirmed`가 거부한다 | 2.5 제안에는 `expires_at`과 확인 코드가 없어, 라이브러리를 직접 부르면 만료·코드 검사 없이 적용됐다 |
| F2 | 만료 판정과 `confirmed_at`은 실제 시계를 쓴다. 호출자가 준 `now`는 `max(now, 현재 시각)`으로만 쓴다 | 과거 `now`를 넘겨 만료된 제안을 적용하거나 `confirmed_at`을 과거로 적을 수 있었다 |
| F3 | apply의 `--ledger`·`--backup-directory`, propose의 `--ledger`, 라이브러리의 `ledger_path`·`backup_directory` 인자를 없애고 상태 파일 경로에서 파생한다 | 빈 원장을 가리키면 원장 확인(`STATE_CHANGED_OUTSIDE_LEDGER`, `LEDGER_INTEGRITY_FAILED`)을 건너뛸 수 있었다 |
| 17번 | `STATE_CHANGED_OUTSIDE_LEDGER`로 적용을 거부하는 경우를 좁힌다. **거부:** 상태 파일 JSON 파싱 실패, 그리고 현재 상태가 원장 마지막 줄의 before-hash와 같은 경우("원장 기록 뒤 상태 쓰기 실패"). **그 밖의 원장 밖 변경:** 경고만 붙여 표에 보이고, 사용자가 확인 코드를 보내면 적용하며, 그 원장 줄에 외부 변경을 기록한다. 원장이 비어 있을 때(첫 적용)의 동작은 테스트로 고정한다 | (§1의 "원장 밖 상태 변경 = 거부" 결정을 대체) |

### 12-2. 수정 내용

| 결정 | 위치 | 내용 |
|---|---|---|
| F1 | `apply_user_confirmed_broker_snapshot.py:252-254` | unresolved 검사 바로 뒤에서 `SCREENSHOT_PROPOSAL_APPLY_NOT_SUPPORTED`로 거부한다. 모든 쓰기보다 앞이다. 이 위치를 고른 이유: 오류 코드를 단언하는 기존 테스트(`test_v25_bs_06`의 revision, `06a`의 source, `26`의 alias, `test_bs_04`, `test_screenshot_proposal_with_unresolved_fields_rejected`의 unresolved)가 그대로 통과한다. 2.5 스키마는 고정 스키마 목록에 남긴다(스키마 검증은 계속함) |
| F2 | 같은 파일 `:255-257`, `:289` | `current_time = real_now if now is None else max(now, real_now)`. 만료(`:273-274`), `confirmed_at`, 백업 파일 이름 시각이 모두 이 값을 쓴다. 호출자의 `confirmation["confirmed_at"]`은 더 이상 쓰지 않는다(이전에는 2.5 경로만 썼다). 시간대 없는 `now`는 비교에서 `TypeError`로 멈춘다(쓰기 전) |
| F3 | 같은 파일 `:201-208`, CLI `reconcile_broker_state.py:196`, `:268`, 파서 | 라이브러리 시그니처에서 두 인자를 뺐다. 원장은 `<상태 폴더>/reconciliation_ledger.jsonl`, 백업은 `<상태 폴더>/backups/`로만 정한다. propose도 같은 규칙으로 원장을 읽는다. alias 검사는 그대로 두었다. 상태 파일 이름이 원장 이름과 같으면 거부된다 |
| 17번(적용) | 같은 파일 `:228-233`, `:281-289`, `:312-313`, `ledger_status` `:53`, `:67` | ① 상태 파일을 UTF-8 JSON 객체로 읽지 못하면 `STATE_CHANGED_OUTSIDE_LEDGER: STATE_FILE_NOT_JSON`(또는 `…_NOT_JSON_OBJECT`)로 거부한다(원장 유무와 무관). ② 원장 마지막 줄의 after ≠ 현재이고 before = 현재이면 `STATE_CHANGED_OUTSIDE_LEDGER: STATE_EQUALS_LAST_LEDGER_BEFORE_HASH`로 거부한다. ③ 그 밖의 after ≠ 현재는 적용하고, 원장 줄에 `state_changed_outside_ledger=true`와 `ledger_expected_portfolio_hash`(원장이 기대한 after 해시)를 남긴다. 평소 적용은 `false`와 `null`이다. `LEDGER_INTEGRITY_FAILED` 거부는 그대로다 |
| 17번(제안·표) | `kiwoom_broker_shadow.py:305`, `:350-356`, `reconcile_broker_state.py:134-139`, `:205`, 문구 JSON | 제안은 `ledger_last_hash_before`를 받는다. ②에 해당할 때만 `STATE_CHANGED_OUTSIDE_LEDGER`를 unresolved에 넣는다(BLOCKED). ③은 경고만 넣는다. 표는 BLOCKED이면 `blocked_STATE_CHANGED_OUTSIDE_LEDGER`(중단) 문구를, 확인 대기이면 `warning_STATE_CHANGED_OUTSIDE_LEDGER`(주의, "확인하면 적용하고 원장에 기록") 문구를 보인다. 스키마 변경은 없다(경고 코드는 이미 enum에 있다) |
| 문서 | `references/broker-snapshot-reconciliation.md:59-63`, `:106-116` | 2.5 적용 거부와 원장·백업 위치 고정을 적었다. Cowork 절차 3번을 중단 경우(무결성 실패, 쓰기 실패형)와 경고 경우(사용자에게 먼저 알리고, 확인하면 적용·기록)로 나눴다 |

**Builder 판단 1건(Judge 확인 대상).** 라이브러리가 ③(원장 밖 변경)을 감지했는데 확인된 제안의 `warnings`에 `STATE_CHANGED_OUTSIDE_LEDGER`가 없으면 `OUTSIDE_LEDGER_WARNING_NOT_IN_PROPOSAL`로 거부한다(`:287-288`).
- 이유: 결정 17은 "경고를 표에 보이고, 사용자가 확인하면 적용"이다. 경고가 없는 제안은 사용자가 그 경고를 본 적이 없다.
- `warnings`는 `proposal_id` 해시에 포함되므로, 경고를 지우거나 더하면 확인 코드가 바뀐다.
- CLI 경로에서는 propose와 apply가 같은 원장을 읽으므로 이 거부가 날 일이 거의 없다. 대상은 라이브러리를 직접 부르는 경우다.
- 원치 않으면 이 두 줄과 테스트 단언 1개를 빼면 된다.

**남겨 둔 것(최소 수정 규칙)**
- `_updated_state`의 스크린샷 분기와 원장 줄의 `if kiwoom else` 분기는 지우지 않았다. `apply_confirmed`에서는 더 이상 닿지 않는다.
- `if kiwoom:` 블록은 들여쓰기를 그대로 두었다. 앞의 F1 거부 때문에 항상 참이다.

### 12-3. 신규 테스트 (8건, `test_reconcile_broker_state.py`)

| 테스트 | 결정 | 단언 |
|---|---|---|
| `LibraryRejectionTests.test_caller_clock_cannot_turn_back_expiry` (:451) | F2 | 실제 시계로 약 1,130초 전에 만료된 제안을 만료 전 시각의 `now`로 적용하면 `BROKER_PROPOSAL_EXPIRED`로 거부된다. 아무것도 쓰지 않는다 |
| `LibraryApplyTests.test_caller_clock_cannot_backdate_confirmed_at` (:659) | F2 | 30일 전 `now`를 줘도 원장 `confirmed_at`은 호출 시각 이후다. 상태 `last_updated_at`, 확인 기록, 감사 파일이 같은 값이다 |
| `LibraryRejectionTests.test_ledger_and_backup_locations_are_not_arguments` (:546) | F3 | `ledger_path`나 `backup_directory`를 넘기면 `TypeError`. 아무것도 쓰지 않고 다른 위치도 생기지 않는다 |
| `CliTests.test_ledger_and_backup_options_are_removed` (:870) | F3 | `propose --ledger`, `apply --ledger`, `apply --backup-directory`가 argparse 오류(종료 코드 2)다. 조회도 쓰기도 없다 |
| `CliTests.test_propose_and_apply_use_the_ledger_next_to_the_state` (:883) | F3·17 | 상태 옆 원장이 쓰기 실패형이면 propose가 BLOCKED(종료 2)이고 show에 중단 문구가 나온다. 원장 밖 변경형이면 확인 대기, 경고만, show에 주의 문구가 나온다. apply 성공 뒤 새 원장 줄은 `state_changed_outside_ledger=true`다 |
| `LibraryRejectionTests.test_unparsable_state_rejected_as_changed_outside_ledger` (:535) | 17 | 깨진 JSON, UTF-8 아님, JSON 배열이면 `STATE_CHANGED_OUTSIDE_LEDGER: STATE_FILE_NOT_JSON…`. 상태 바이트 불변, 백업·원장·감사 파일 없음 |
| `LibraryApplyTests.test_first_apply_with_a_missing_or_empty_ledger` (:673) | 17 | 원장이 없을 때와 빈 파일일 때: `ledger_status`가 (0건, 체인 정상, after·before 없음)이다. 제안에 경고가 없고 적용된다. 원장 줄은 1개이고 `previous_entry_sha256=0×64`, `state_changed_outside_ledger=false`, `ledger_expected_portfolio_hash=null`이다 |
| `LibraryApplyTests.test_outside_ledger_change_applies_after_confirmation_and_is_recorded` (:702) | 17 | 원장 밖 변경을 경고로 보인 제안을 적용하면 원장이 2줄이고 체인이 정상이다. 새 줄은 외부 변경 `true`, 기대 해시 `f…`, 이전 줄 해시를 연결한다. 다음 적용은 원장과 맞으므로 `false`다 |

바꾼 기존 테스트 6건은 §4 표 아래 "Judge FAIL 수정에서 바뀐 기대"에 적었다.

### 12-4. 검증

| 항목 | 결과 |
|---|---|
| 대상 테스트 (수정 전 → 후) | `test_reconcile_broker_state` 48 OK → 56 OK. `test_v2_5_broker_snapshot` 27 OK → 27 OK. `test_v2_6_broker_beginner` 25 OK → 25 OK. `test_kiwoom_broker_shadow` 24 OK → 24 OK |
| 새 테스트가 옛 코드에서 실패하는지 | 바뀐 테스트 3개 모듈을 `dfb7f7b`의 스크립트 3개(scratchpad 복사본)에 대고 돌렸다. 108건 중 19건(하위 테스트 포함)이 실패·오류였다. 모두 신규 8건과 바꾼 6건이고, 나머지는 통과했다 |
| 스키마 감사 `validate_schema_contracts.py` | PASS |
| 고정 파일 16개, `alert_policy.json`, `workspace/policies/`, `SKILL.md`, `portfolio_state.json` | `git diff HEAD` 비어 있음 |
| 줄바꿈 | 기존 CRLF 파일 6개는 CRLF만, I0 신규 LF 파일 4개(CLI, 테스트, 문구, 이 보고서)는 LF만이다. 섞인 파일은 없다 |
| 전체 테스트 (서브에이전트, 1회) | 1,924건(1,916 + 신규 8), `FAILED (failures=23, errors=291, skipped=1)`. 실패 314줄이 §3-2의 2차 실행 목록과 한 줄씩 같다. **새 실패 0, 해소 0** |

**검증 중 정리한 것**
- 옛 코드로 돌린 확인 실행에서 `test_v25_bs_05`가 옛 동작대로 적용됐다.
- 그 결과 git 제외 폴더 `workspace/outputs/v2_5_shadow/`에 `backups/`와 `reconciliation_ledger.jsonl`이 생겼다. 합성 테스트 상태 1건이다.
- 내용을 확인한 뒤 지웠고, 폴더는 원래대로(`.gitkeep`, `fixture-acceptance/`)다.
- 새 코드에서는 이 경로로 쓰기가 일어나지 않는다(F1).

### 12-5. 이 절이 대체하는 이전 서술

- §1 "원장 밖 상태 변경" 행 → 12-1의 17번.
- §8 "만료 검사 적용 범위(4a)"와 "스크린샷 경로" → 2.5 제안은 라이브러리가 거부한다(F1).
- §8 "쓰기 실패 때의 동작"은 그대로 맞다. 원장 마지막 줄 before = 현재 상태이므로 propose는 BLOCKED이고 적용은 거부된다.
- §7 1·2·7번의 `apply…` 줄 번호는 12-2 기준으로 읽는다. 쓰기 순서는 백업 `:296` → 원자료 재확인 → 원장 `:316` → 원자적 교체 `:317`이다.

### 12-6. 남은 확인 필요

- 상태 파일이 JSON이 아니면 `propose`는 BLOCKED 제안을 만들지 않고 예외로 멈춘다(`load_json`). 쓰기는 없다(fail-closed). 표로 보여 줄지는 범위 밖이라 두었다.
- 원장 밖 변경을 적용한 뒤의 복원 절차와 쓰기 실패형의 복원 절차는 P4 §5 대기 항목 그대로다.
- 스크린샷 경로를 다시 열려면 만료·확인 코드·원장 규칙을 2.5 제안에 먼저 넣어야 한다(별도 K3 작업).
