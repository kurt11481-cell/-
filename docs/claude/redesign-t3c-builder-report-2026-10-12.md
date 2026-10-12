---
id: redesign-t3c-builder-report-2026-10-12
title: 재설계 T3c Builder 보고 — 권한 경로 보강 + N1 false 허용 + ORDER_TICKET_HUMAN_ENTRY 고정 + CLAUDE.md 키움 승인 고정 문구 정정
date: 2026-10-12
status: Builder 완료 — BLOCKED 아님. 커밋·병합 안 함(Judge 대기)
prompt: docs/claude/redesign-t3c-builder-prompt-2026-10-12.md
worktree: .claude/worktrees/t3c (branch codex/master-recovery-expansion, HEAD f8185fc)
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: T3c Judge(지시문 6절 K1~K7) · Cowork 병합 안내 · 관제판 redesign-t3c
---

## 1. 0단계 (읽기만)

**a. 전체 스위트 기준선** (변경 전, clean worktree; test-runner 서브에이전트로 실행, 숫자는 원본 출력에서 직접 셈)

- `Ran 2908 tests` · `FAILED (failures=19, errors=9, skipped=3)` · 실패/오류 줄 28 = 예상(T3b Judge 기준 28)과 같다.
- 실패 id 묶음: `test_v2_6_7_session_aware_kiwoom_priority` 14줄(subTest 4 포함), `test_nbis_v4_kiwoom_price_authority` 2, `test_materialize_kiwoom_session_aware_acceptance_candidate` 2, setUpClass 3(`test_holding_baseline_observation_audit`·`test_mvll_canonical_volume_lineage`·`test_provider_limitation_audit`), 그 밖 1개씩 7(`test_instrument_identity_authority` test_15, `test_materialize_instrument_identity_artifact`, `test_evaluate_timing_integration` i0b, `test_portfolio_decision_dashboard` grade_b, `test_portfolio_decision_order_intent` lmt, `test_nbis_v3_shadow_activation`, `test_validate_research_packet` snapshot — 합 28). `test_dev_pipeline`·`test_reconcile_broker_state`·`test_auto_core*` 실패 0.
- 시각 주의: 기준선 실행은 14:57:15에 시작했고 이 묶음의 첫 편집은 15:00 이후다. unittest discover는 실행 전에 모든 모듈을 읽으므로 devpipe·test_dev_pipeline은 옛 판이 쓰였다. 실행 중 파일을 다시 읽는 테스트(authority-paths.txt)는 새 줄이 있어도 같은 결과(새 패턴도 실제 파일에 걸림). CLAUDE.md는 기준선 끝(Ran 확인) 뒤에 고쳤다. 실패 집합이 예상 28과 같고 dev_pipeline 실패가 0이라 기준선으로 쓴다.

**b. base sha256** — 4개 모두 머리말과 같다(BLOCKED 아님).

| 파일 | sha256 | 머리말 |
|---|---|---|
| CLAUDE.md | 2d2f914cc31b7cb4f0e539057c57e3e9715989dcdbcedd3be2691d3ba724e3ce | 2d2f914c… 일치 |
| tools/dev_pipeline/authority-paths.txt | b28ab669bb1bd3ea465e7d69bb97138a628216eb3f4f737b220276eedfd88ea6 | b28ab669… 일치 |
| tools/dev_pipeline/devpipe.py | c24ebb1f3aa1c3407e54d7d6d45f2a91b75789796a31712e93f4ffce27bcfe6d | c24ebb1f… 일치 |
| tools/dev_pipeline/README.md | edd6890e943e76c2c2e3e487869f5d89f2126ba77706600c845c1ae3046fe8c0 | edd6890e… 일치 |

- HEAD는 머리말의 29ad21d가 아니라 f8185fc다. 29ad21d는 HEAD의 조상이고 그 사이 7커밋은 `docs/claude/`만 바꿨다(이 지시문 커밋 포함). 4개 파일 해시가 같으므로 진행.

**c. 권한 경로 후보 존재** — 모두 있음.
- `docs/claude/card-evidence-registry.json`
- `manage-us-stock-strategy/schemas/auto-core-*.schema.json` 8개: auto-core-card-registry · auto-core-compare · auto-core-config · auto-core-decision · auto-core-replay · auto-core-research-record · auto-core-result · auto-core-ticket.

**d. CLAUDE.md 문구 단언 grep** — tests·scripts·tools에서 CLAUDE.md를 읽는 테스트는 `test_reconcile_broker_state.py:959-968`(`test_agent_rules_require_snapshot_and_user_confirmation`: "only from a verified read-only broker snapshot", apply/auto-core invariant, "Never infer fills…")뿐. `kiwoom-acceptance-pin`·`acceptance`를 CLAUDE.md 텍스트로 단언하는 테스트는 없다. `test_dev_pipeline.py`의 CLAUDE.md는 보호 경로 이름으로만 쓰이고(:94, :172, :369, :1214, :1382) `test_scheduled_prompt_kiwoom_profile.py:3`은 docstring.

## 2. 바꾼 파일·줄

`git diff --stat`: 6파일(CLAUDE.md, README.md, authority-paths.txt, devpipe.py, judge-prompt.md, test_dev_pipeline.py) + 이 보고(새 파일). 허용 경로 밖 변경 0, .ps1 변경 0. 바뀐 파일 모두 CRLF만(LF 단독 0), BOM 없음.

| 파일 | 줄 수(CRLF=LF) | 변경 뒤 sha256 |
|---|---|---|
| CLAUDE.md | 115 → 116 | 846f0fb240cdf8ca79f54ba6610c17c2fef98486710fa95f4a102d2ea585dd72 |
| tools/dev_pipeline/authority-paths.txt | 61 → 65 | d6ad601250fcaecc0f4a2879a0f1dbe28f8a0b3f2c58ecfaf3f0f3480030e22e |
| tools/dev_pipeline/devpipe.py | 2193 → 2194 | 94c6e8bbe0f5ccbe34a5cccebaf7b1b93c9782a049abc7f001f34784b237d3fb |
| tools/dev_pipeline/README.md | 89 → 91 | 6a32133d02e9b0b1b2757652405d9053cd862530f4ddf9ceb065fd76a2b2db44 |
| tools/dev_pipeline/judge-prompt.md | 38 → 38 | 877d34e27335bdc678e8ba2e707bca86bc913ec491cd7b216129c3c586632b6d |
| manage-us-stock-strategy/tests/test_dev_pipeline.py | 1436 → 1467 | 997a5251c3311ac7b2bce7c912930ba11dc90a7cfdcc042ab2f07113042cf5cd |

**A. authority-paths.txt** — 파일 끝(“Approved products and new-buy approval” 블록 뒤)에 빈 줄 + 4줄만 추가(62~65줄). 기존 줄 diff 0.
```
# Auto-core order-ticket evidence and contracts (T2, 2026-10-12; evidence: docs/claude/redesign-t2-builder-report-2026-10-10.md)
docs/claude/card-evidence-registry.json
manage-us-stock-strategy/schemas/auto-core-*.schema.json
```
- 테스트: `test_authority_paths_cover_auto_core_contracts`(test_dev_pipeline.py:1428) — 두 패턴이 파일에 있고, 등록부 1 + 스키마 8개가 존재하며 매치, `holding-card.schema.json`·`automation-delivery-runtime.schema.json`·`docs/claude/watchlist-registry.json`은 매치 없음. 기존 `test_authority_paths_file`(:1394)의 "각 패턴이 실제 파일에 걸린다" 반복 검사도 새 패턴에 통과.

**B. devpipe.py N1** — 136~138줄. 주석 1줄 추가 + 상수 1줄 변경. 그 밖 diff 0. P6 보호 상수(`PROTECTED_PREFIXES`·`PROTECTED_GLOBS`·`PROTECTED_NAMES`·`PROTECTED_DIR_NAMES`, 102~120줄) 바이트 그대로(diff 범위 밖).
```
# quantity_authority false = no authority (repository meaning; evidence docs/claude/redesign-t3b-judge-report-2026-10-10.md K6).
ADDED_NONE_VALUES = {"quantity_authority": ("none", "null", "$null", "false", "$false"),
                     "execution_quantity": ("null", "none", "$null")}      # 이 줄 변경 없음
```
- 테스트(test_dev_pipeline.py `AddedLineMarkerTests`): `test_raising_values`(:1054)에서 `'"quantity_authority": {"const": false}'`를 빼고 `quantity_authority: true`·`execution_quantity: false`를 더함(`quantity_authority = "full"`·`quantity_authority: 5`·`{"enum": ["none", "full"]}`는 원래 있음). `test_values_that_stay_general`(:1065)에 `'"quantity_authority": {"const": false}'`·`quantity_authority: false`·`quantity_authority = $false`·`'"quantity_authority": false'` 추가. REMOVED_LINE 단언(`test_schema_approval_const_change_raises_class`, :413 — `{"const": false}` → `true` 변경이 `REMOVED_LINE:quantity_authority`로 authority)은 그대로 통과.

**C. ORDER_TICKET_HUMAN_ENTRY** — 코드 변경 0.
- 테스트 `test_order_ticket_marker_stays_authority`(:1079): `"quantity_authority": "ORDER_TICKET_HUMAN_ENTRY"`, `quantity_authority = "ORDER_TICKET_HUMAN_ENTRY"`, `"quantity_authority": {"const": "ORDER_TICKET_HUMAN_ENTRY"}` → 정확히 `["ADDED_LINE:quantity_authority"]`. CLAUDE.md형 산문 줄(`… (quantity_authority "ORDER_TICKET_HUMAN_ENTRY", tickets only)`) → `[]`(현행 동작 단언).
- README.md:57 "`quantity_authority` ≠ none/null" → "≠ none/null/false". README.md:59(새 줄, 앞에 빈 줄): "`ORDER_TICKET_HUMAN_ENTRY`(주문 1단계 표지)는 `quantity_authority` 값이 none이 아니므로 새 줄에 쓰이면 authority다 — 의도된 동작이며, 주문표 모듈은 이미 권한 경로다." (주문표 모듈 `auto_core_tickets.py`는 authority-paths.txt:12 `manage-us-stock-strategy/scripts/auto_core*.py`에 걸림.)
- judge-prompt.md:23 G7 끝에 "quantity_authority를 none/null/false가 아닌 값(예: ORDER_TICKET_HUMAN_ENTRY)으로 추가하면 class_ok=false." 다른 문장 변경 0.

**D. CLAUDE.md** — "## Change classes" 절 59~61줄(3줄) → 59~62줄(4줄). 다른 줄 diff 0. `only from a verified read-only broker snapshot` 유지(test_reconcile_broker_state 56건 OK).
```
- Kiwoom acceptance pin: retired by redesign T1 (merged 510961a). manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json
  has status RETIRED and is kept as the list of formerly pinned files. Editing one of them no longer invalidates an
  acceptance; instead every auto-core run records the git commit SHA and dirty paths, and in apply mode an uncommitted edit to a guarded
  file (former pin list, the core's own files, tracked files under manage-us-stock-strategy/scripts, schemas, assets) fails before any read (docs/claude/redesign-t1-builder-report-2026-10-10.md F6).
```
근거(파일:줄):
- RETIRED: `manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json:52` `"status": "RETIRED"`, :53 `retired_at 2026-10-10`, :54 retirement_note("The list is kept as that guarded set").
- 510961a: `git log -1 510961a` = "feat: auto-core T1 (collect, invariant reconciliation, exposure) with r2/r3 Judge conditions".
- SHA·dirty 기록: `auto_core_reconcile.py:1152-1199` `git_provenance`(commit SHA, `dirty_paths`, `guarded_dirty_paths`); 결과 기록 `auto_core.py:304`.
- guarded 집합: `auto_core_reconcile.py:1105-1112` `AUTO_CORE_GUARDED_PATHS`(코어 자체 6파일), :1113-1116 `GUARDED_PREFIXES`(scripts/·schemas/·assets/ 아래 추적 파일 전부, T1 r3 C2), :1137-1149 `guarded_paths`(옛 고정 목록 ∪ 코어 파일 ∪ pin scope 자신).
- apply 모드 읽기 전 FAIL: `auto_core_reconcile.py:1203-1210`("in apply mode, unknown provenance or an uncommitted guarded file is a FAIL before any read"; `GUARDED_FILES_UNCOMMITTED`). decide 실행도 같음(`auto_core_decide.py:5`).
- T1 보고 F6: `docs/claude/redesign-t1-builder-report-2026-10-10.md:62`.

**테스트 수치**

| 대상 | 결과 |
|---|---|
| `test_dev_pipeline*` | Ran 120, OK (새 테스트 2: `test_order_ticket_marker_stays_authority`, `test_authority_paths_cover_auto_core_contracts`; `def test_` 120 → 122, 실행 수는 전체 스위트 차이 +2로 확인) |
| `test_reconcile_broker_state*` | Ran 56, OK |
| `test_auto_core*` | Ran 287, OK (skipped=1) |
| 스키마 감사 `validate_schema_contracts.py` | `"status": "PASS"`, errors [] |
| 전체 스위트(변경 후) | `Ran 2910` · `FAILED (failures=19, errors=9, skipped=3)` · 실패/오류 줄 28 |
| 기준선 대비 | Ran +2(= 새 테스트 2), 새 실패 0, 고쳐진 실패 0 → 실패 집합 = 기준선(⊆ 성립), 테스트 수 감소 0 |

**기계 실측 원문** (모델 호출 없음; `devpipe.parse_authority_patterns` + `glob_to_regex`, `git ls-files` 전체, 전 = `git show HEAD:tools/dev_pipeline/authority-paths.txt`)
```
git ls-files total: 1354
authority hits before: 60 after: 68 diff: 8
removed: []
newly matched:
  docs/claude/card-evidence-registry.json
  manage-us-stock-strategy/schemas/auto-core-card-registry.schema.json
  manage-us-stock-strategy/schemas/auto-core-compare.schema.json
  manage-us-stock-strategy/schemas/auto-core-decision.schema.json
  manage-us-stock-strategy/schemas/auto-core-replay.schema.json
  manage-us-stock-strategy/schemas/auto-core-research-record.schema.json
  manage-us-stock-strategy/schemas/auto-core-result.schema.json
  manage-us-stock-strategy/schemas/auto-core-ticket.schema.json

added_value_reasons samples:
  quantity_authority: false                                      -> []
  quantity_authority = $false                                    -> []
  "quantity_authority": false                                    -> []
  "quantity_authority": {"const": false}                         -> []
  quantity_authority: true                                       -> ['ADDED_LINE:quantity_authority']
  quantity_authority = "full"                                    -> ['ADDED_LINE:quantity_authority']
  quantity_authority: 5                                          -> ['ADDED_LINE:quantity_authority']
  "quantity_authority": {"enum": ["none", "full"]}               -> ['ADDED_LINE:quantity_authority']
  execution_quantity: false                                      -> ['ADDED_LINE:execution_quantity']
  "watchlist_approved": true                                     -> ['ADDED_LINE:watchlist_approved']
  "quantity_authority": "ORDER_TICKET_HUMAN_ENTRY"               -> ['ADDED_LINE:quantity_authority']
  quantity_authority = "ORDER_TICKET_HUMAN_ENTRY"                -> ['ADDED_LINE:quantity_authority']
  "quantity_authority": {"const": "ORDER_TICKET_HUMAN_ENTRY"}    -> ['ADDED_LINE:quantity_authority']
  quantity_authority "ORDER_TICKET_HUMAN_ENTRY" (tickets only)   -> []
```
기대(등록부 1 + 스키마 7 = +8, config는 원래 있음)와 같다.

## 3. Builder 판단 목록

1. **D 문구를 근거에 맞게 고침(사실 추가 아님, 범위 정정).** 지시문 괄호 "(the former pin list plus the core's own files)"는 guarded 집합보다 좁다. 코드는 T1 r3 C2로 `manage-us-stock-strategy/scripts/`·`schemas/`·`assets/` 아래 추적 파일 전부도 지킨다(auto_core_reconcile.py:1113-1116, :1196-1197; pin scope :54 retirement_note도 같은 말). 그대로 쓰면 "그 밖 scripts 파일은 미커밋이어도 된다"로 읽힐 수 있어 괄호를 "(former pin list, the core's own files, tracked files under manage-us-stock-strategy/scripts, schemas, assets)"로 바꿨다. 줄 수는 지시대로 4줄(115 → 116).
2. **D "kept only as" → "kept as".** pin scope 파일은 guarded 목록 외에 `allowed_predecessor_drift`(옛 후보 도구 자기일관성용)도 담고 있어(:54) "only"는 사실보다 강하다. 한 낱말 뺐다.
3. **devpipe.py 128~131줄 N1 설명 주석은 고치지 않음.** 거기 "a quantity_authority other than none/null"은 이제 none/null/false가 맞지만, 지시문이 "그 밖의 devpipe.py 줄은 바꾸지 않는다"고 해서 새 주석 1줄(136줄)로만 보완했다. Judge가 원하면 다음 보호 경로 변경 때 한 낱말 맞춘다.
4. **문자열 `"false"`도 general.** `added_value_reasons`는 값의 따옴표를 벗긴 뒤 비교하므로(devpipe:836) `"quantity_authority": "false"`도 none 쪽이다. `"none"` 문자열과 같은 처리이고, 저장소에 이 형태는 없다. 별도 테스트는 넣지 않았다(지시 목록 밖).
5. 테스트 목록 위치: 지시문의 "1056~1072 부근 목록"을 그대로 고쳤다. `execution_quantity: false`는 authority 쪽에 새로 넣었다(지시 "authority 쪽에 남는 것"에 들어 있으나 원래 목록엔 없었음).

## 4. 남는 위험

- **`portfolio_review_journal.py`·`portfolio-review-journal-payload.schema.json`은 권한 경로가 아니다(이번에 판단하지 않음, 지시대로).** 둘 다 `ORDER_TICKET_HUMAN_ENTRY` 권한 블록을 담는다(portfolio_review_journal.py:74 `TICKET_AUTHORITY`, schema:70 `{"const": "ORDER_TICKET_HUMAN_ENTRY"}`). 그 줄을 고치거나 새로 쓰면 REMOVED_LINE/ADDED_LINE으로 authority가 되지만, 주문표 기록 형식의 다른 부분(필드 집합·검증 논리)을 바꾸는 작업은 general로 통과할 수 있다. 판단은 Cowork/사용자 몫.
- 기준선 실행 도중 편집(1-a 시각 주의). 결과 집합이 예상 28과 같아 영향은 없다고 보지만, Judge가 clean HEAD에서 다시 재면 확정된다.
- B는 새 줄의 `quantity_authority: false`만 general로 내린다. 기존 줄을 false로 바꾸는 경우는 REMOVED_LINE으로 여전히 authority(:413 테스트).
- 이번 변경으로 카드 등록부·auto-core 스키마를 건드리는 파이프라인 작업은 NEEDS_APPROVAL로 간다(지시문 4절 2 — INDEX.md 반영은 Cowork).
