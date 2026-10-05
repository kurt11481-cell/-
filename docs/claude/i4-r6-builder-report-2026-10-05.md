# I4 R6·R7 Builder 보고 — Kiwoom acceptance 고정 범위 재설계 (2026-10-05, K3)

- 역할: I4 R6·R7 Builder. 지시문: `docs/claude/system-review-p4-roadmap-2026-09-30.md` 부록 A7
- worktree `gov-r6`, 브랜치 `worktree-gov-r6`, 시작 HEAD `5dd739f`
- 커밋
  - R6 `e42f9db`(사용자 승인)
  - R6 보완 `48798d1`(사용자 승인): 고정 테스트 2개. 도우미를 파일 안으로 옮기고, 게이트 AST 단언을 추가했다(§3-4, §5-3)
  - R7 후보 `45cf1888…`와 이 보고서: 마지막 커밋으로 승인 요청
- 권한: `order_authority=false`, `quantity_authority=none`, `execution_quantity=null` 그대로.
  - 활성화(R9)는 하지 않았다.
  - 정책·상태 파일, `decision_journal.json`, `alert_policy.json`, `SKILL.md`, `CLAUDE.md`는 diff 0이다.
  - 키움 도구는 쓰지 않았다(명세 파일 `kiwoom_api_spec.json`만 읽음).

## 0. 판정 위치 (0단계)

- worktree에서는 원시 해시 테스트를 판정할 수 없다.
  - acceptance manifest의 원시 해시가 원본 `f0bab…`, worktree `0a7de90c…`로 다르다.
  - 추적 파일 906개 중 376개가 원본과 바이트가 다르다. 차이는 모두 줄바꿈뿐이다.
  - 원본 폴더의 줄바꿈이 섞여 있다(git blob과 같은 LF 327개, CRLF 574개). 그래서 어떤 체크아웃 설정으로도 원본을 재현할 수 없다.
- **사용자 결정 (가):** 원본 폴더를 바이트 그대로 저장소 밖(scratchpad `origcopy`)에 복사하고, worktree diff를 적용해 판정한다.
  - 복사본은 `.claude`(worktree들)·`.runtime-cache`만 뺐다. `.git` 14.8MB는 포함했다.
  - 복사 직후 추적 파일 906개가 원본과 모두 같았고, manifest는 `f0bab…`였다.
- R7 후보 생성도 같은 복사본에서 했다.
- 모의 활성화는 복사본의 복사본 `simcopy`에서만 했다(§4-3).

## 1. 기준선 (1단계, `origcopy`, HEAD `5dd739f`, Python 3.13.15)

`Ran 2399` / `FAILED (failures=9, errors=16)`.

| 묶음 | 건수 | 테스트 |
|---|---|---|
| acceptance 관련 | 17 | materialize 15건: `test_01`, `02`, `03`, `03a`, `04`, `05`, `06`, `07`, `08`×3(BRK.B·BRKb·COST), `09`, `09a`, `09b`, `10`. 원인 `current active Acceptance invalid`(테스트가 08-26 manifest `2994…`를 활성으로 하드코딩했는데 정책은 `f0bab…`를 가리킴). v2_6_7 2건: `test_extended_provider_scope_candidate_validates_without_activation`, `test_guarded_priority_requires_locked_acceptance_manifest`(구현 해시 불일치 2개) |
| 환경·상태 의존 | 8 | `test_save_daily_pipeline`(`pypdf` 없음). dashboard 2건(상태 파일 NBIS 13, 테스트 기대 15). `test_sec_scheduled_shadow` 01·05·23(PowerShell `Join-Path`에 `$PSScriptRoot` 빈 값), 35·37(`SEC_ACCESS_BLOCKED`가 PowerShell 5.1에서 NativeCommandError) |
| 기타 | 0 | — |

- SEC 05는 한글 사용자 경로 때문에 cp949 디코드 오류로 원인이 가려져 있었다. `PYTHONUTF8=1`로 다시 돌려 같은 `Join-Path` 원인을 확인했다.
- worktree에서만 나는 실패(`INTEGRITY_FAILURE`, 신원 artifact 원시 해시)는 위치 의존이다. 복사본에서는 0건이다.

## 2. 계획 때 정한 것 (2단계, 사용자 승인)

| 항목 | 정한 것 | 근거 |
|---|---|---|
| 2a 고정 범위 | 새 고정 범위 27개(§3-1 ③) | P3 §8-2, HEAD 기준으로 다시 뽑음 |
| 2a 현금흐름 묶음 | **포함**: `scripts/cash_flow_evidence.py`, `schemas/kiwoom-cash-flow-evidence.schema.json`, `schemas/cash-flow-declaration.schema.json`, `assets/kiwoom-transaction-history-classification.json` | `reconcile_broker_state.py:24`가 직접 import한다. 그 결과(입출금 신고 블록)가 apply를 거쳐 원장에 기록된다 |
| 2a 결정 원장 경로 | 넣지 않음(`portfolio_review_journal.py`, `score_decision_journal.py`) | 키움 acceptance와 무관 |
| 2b S7 2차 | 파일 단위로 겹치지 않음. 간접 의존 2건은 §7에 남김 | S7 보고 §2.2 "2차" 표, §5.6 |
| 2c ⑨ ADD-T | **제외** | 사용자 답: 안 B′ 병합 뒤 라이브 수동 분석에서 보조 조회 FAIL 없음 |
| 2d R7 증거 | **08-13/14 증거 재사용** | 사용자 결정(핀 진단 §5-2 권장). 후보는 활성 manifest의 검증 필드와 원천 증거 9개 참조를 그대로 잇는다. 새 실시간 조회는 하지 않았다 |
| 2e 범위 밖 종목 | 추가하지 않음, 목록만 보고(§7-8) | A7 2e |
| ⑥ 범위 | 도구·검증기만 정규화한다. `test_v2_6_7`의 helper와 CRLF·BOM 테스트는 바꾸지 않는다 | 사용자 결정. 기존 기대값 변경 없음 |
| 고정 목록 위치 | `workspace/policies/`가 아니라 고정 대상 asset `manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json` | A7 규칙상 정책 파일을 고칠 수 없다. 15종목은 활성 정책을 읽기만 해서 얻는다 |
| materialize 테스트 | 현재 전환으로 다시 쓴다(§5-2) | 08-26→08-28 일회성 상태는 재현할 수 없다 |
| R7 완료 기준 | materialize 15건은 해소한다. v2_6_7 2건은 R9 전에는 원리상 해소할 수 없으므로 모의 활성화로 확인한다 | 활성 `f0bab…`를 현재 코드로 검증하는 테스트다 |

## 3. 구현 (3단계)

### 3-1. 항목별 (커밋 `e42f9db`)

| # | 내용 | 파일 |
|---|---|---|
| ① | materialize는 활성 manifest를 정책 바인딩으로 찾는다(증거 폴더에서 정규화 해시가 같은 파일이 정확히 1개여야 한다). 활성 검증 오류는 `implementation hash mismatch: <경로>`이면서 허용 목록에 있는 경로일 때만 넘긴다(§3-3). 나머지 오류는 모두 FAIL이다. 실제 드리프트는 후보 `predecessor_implementation_drift`에 `{경로, 고정 해시, 현재 해시}`로 기록한다. 11·15종목 상수는 1.2 경로에서 쓰지 않는다. 종목은 활성 정책 순서를 쓰고, 후보 정책 순서가 다르면 FAIL이다 | `materialize_…candidate.py`, `validate_…candidate.py` |
| ② | 보호 기능을 고정 모듈 2개로 옮겼다. `run_manual`은 같은 이름으로 다시 import한다. 옮긴 함수 10개는 원본 `5dd739f`와 소스가 같다(AST 비교). 바뀐 곳은 ⑧과 주입 seam 두 곳뿐이다(§5-3) | `manual_data_guards.py`, `scheduled_input_gate.py`, `run_manual_portfolio_analysis.py` |
| ③ | 고정 목록 27개 = 데이터 정확성 10 + 보호 모듈 2·전용 테스트 2 + 경계 테스트 1 + 상태 쓰기 6 + 현금흐름 묶음 4 + pin-scope와 그 스키마 2. 해제: `run_manual`, `test_manual`, 도구 4개 | `assets/kiwoom-acceptance-pin-scope.json`, `schemas/kiwoom-acceptance-pin-scope.schema.json` |
| ④ | `schema_version` 1.2, `hash_governance`에 새 값 추가, 엄격한 `candidate_governance` 블록 추가. 1.0·1.1 정의는 바꾸지 않았다(`hash_governance`만 const → enum 2값). 1.2 후보에는 옛 원시 블록(`authority_bindings`, `provider_scope_contract`)이 있으면 FAIL이다 | `kiwoom-session-aware-acceptance-manifest.schema.json` |
| ⑤ | `_return_code_ok`는 명시적 0(`0`, `"0"`, `"0000"`)만 성공으로 본다. 누락이면 `KIWOOM_RETURN_CODE_MISSING`, `null`·0 아닌 값·bool이면 `KIWOOM_API_UNAVAILABLE`이다. 근거: 명세상 6개 API(`usa10098`, `10099`, `10100`, `10104`, `06012`, `20100`) 응답에 모두 `return_code`가 있다. `kiwoom_candidate_discovery_bridge`도 같은 함수를 쓰므로 함께 엄격해진다 | `kiwoom_runtime_bridge.py` |
| ⑥ | 1.2 후보의 권한 바인딩 4개, pin-scope 바인딩, `supersedes`, 정책 해시를 정규화 해시로 만든다. 1.1 후보는 지금처럼 원시 해시로 검증한다. 원천 증거 9개는 원시 해시로 그대로 검사한다(후보 단계에서는 반드시 있어야 함) | 위 두 도구 |
| ⑦ | `main()`이 `code_provenance`를 기록한다: `git_commit`, `git_branch`, `manage-us-stock-strategy/` 한정 dirty 여부(미추적 포함), `k3_evidence_eligible`. git 호출은 `--no-optional-locks`를 쓴다. dirty이거나 확인할 수 없으면 `unknowns`에 `DIRTY_CODE_TREE`·`CODE_PROVENANCE_UNAVAILABLE`을 넣고 K3 증거 자격을 주지 않는다. 분석과 등급은 바꾸지 않는다. 선택 인자라 기존 호출의 보고서는 그대로다 | `run_manual_…py`, `manual-portfolio-analysis.schema.json` |
| ⑧ | 정규화 예외가 나면 `UNAVAILABLE`과 `normalization_status=BROKER_SNAPSHOT_NORMALIZATION_FAILED`를 기록하고 hard fail한다. 보유내역 조회를 요청했으면 `BROKER_HOLDINGS_UNAVAILABLE`도 함께 붙는다. 빈 보유를 broker 근거로 쓰지 않는다 | `manual_data_guards.py`, `run_manual_…py` |

### 3-2. 바뀐 파일

- R6 `e42f9db`: 16개, 모두 `manage-us-stock-strategy/` 아래.
  - 수정 7개: 스키마 2개, `kiwoom_runtime_bridge.py`, materialize, 후보 검증기, `run_manual`, materialize 테스트.
  - 새 파일 9개: 보호 모듈 2, pin-scope와 그 스키마, 새 테스트 5개(`test_manual_data_guards`, `test_scheduled_input_gate`, `test_state_write_boundary`, `test_manual_code_provenance`, `test_kiwoom_runtime_return_code`).
- R6 보완 `48798d1`: `tests/test_state_write_boundary.py`(도우미를 파일 안으로 옮김), `tests/test_scheduled_input_gate.py`(AST 단언 1건 추가) 2개.

### 3-3. 드리프트 허용을 `f0bab…`에 묶은 설계 (Judge 확인 대상)

**무엇을 했나**
- pin-scope asset에 `allowed_drift_predecessor_sha256 = f0bab7101b61…`과 `allowed_predecessor_drift` 6개 경로를 둔다.
- 판정 함수는 `allowed_drift_for(pin_scope, predecessor)`(`validate_…candidate.py`)다.
  - 허용이 묶인 ID가 지금 대체하려는 선행 ID와 같을 때만 그 6개 경로 목록을 돌려준다. 다르면 빈 목록을 돌려준다.
- materialize(생성 전 선행조건)와 후보 검증기(1.2 경로)가 같은 함수를 쓴다.
- 선행 manifest를 운영 검증기로 검증해서 나온 오류는 둘로 나뉜다.
  - 넘어가는 것: `implementation hash mismatch: <허용 목록 경로>`.
  - 나머지: 해시 아닌 오류, 허용 목록 밖 드리프트, 파일 누락은 모두 FAIL이다.

**계획(첫 구현)과 달라진 점**
- 첫 구현은 "허용이 지금 선행에 묶여 있지 않으면 드리프트가 없어도 FAIL"이었다.
- 지금은 묶인 ID가 드리프트를 넘길 때만 의미가 있다. 드리프트가 0이면 허용이 필요 없고, 운영 검증기 오류가 0개여야 통과한다.

**왜 바꿨나**
- R9 뒤에는 활성이 새 후보가 된다. pin-scope는 여전히 `f0bab…`에 묶여 있다.
- 첫 구현대로면 드리프트가 전혀 없어도 다음 후보를 만들 수 없다. materialize 테스트도 다시 깨진다(모의 활성화에서 재현됨).
- 다음 전환마다 "드리프트 없음"을 적으려고 고정 asset을 고쳐야 하는 교착이 생긴다. 바로 P3 §8-1이 지적한 교착과 같은 종류다.

**약화가 아닌 이유**
- 드리프트가 있을 때는 첫 구현과 같다. 묶인 선행이 일치하고 경로가 목록에 있어야 한다.
- 다른 선행에 묶인 허용은 드리프트를 하나도 넘기지 못한다(`test_14`).
- 기록된 드리프트는 다시 계산한 값과 같아야 한다(`test_19`). 목록 밖 드리프트는 기록이 맞아도 FAIL이다(`test_20`).

**남는 점**
- R9 뒤 pin-scope에는 더 쓰이지 않는 `f0bab…` 허용이 남는다. 다른 선행과는 일치하지 않으므로 효과는 없다.
- 이 허용을 새 선행으로 다시 묶으려면 고정 asset을 고쳐야 하고, 그러면 새 후보 해시가 바뀐다. 즉 K3 경로다.

**Judge에게 묻는 것**
- "묶인 선행에서 목록에 있는 구현 드리프트만 넘김"이 P3 §8-3 ①의 "허용된 드리프트 목록" 취지와 원래 선행조건("활성이 완전히 유효")을 적정하게 대체하는가.

### 3-4. 계획과 달라진 그 밖의 점

| 달라진 점 | 이유 |
|---|---|
| ⑤에서 bool도 거부한다 | 새 테스트가 `return_code: false`가 통과하는 빈틈을 잡았다(`False == 0`) |
| `validate_scheduled_input`과 `_normalize_broker_state`는 `run_manual`에 얇은 wrapper를 남겼다 | 기존 테스트가 `run_manual`의 `derive_run_provenance`·`_acquisition_complete_cutoff`를 patch한다. wrapper가 그 이름을 호출 시점에 넘기므로 기존 단언이 빈 단언이 되지 않는다. 대신 고정 함수에 주입 인자가 생겼다(§5-3) |
| 후보 파일 이름이 `session-aware-priority-acceptance-inactive-superseding-candidate.json`으로 바뀌었다 | 옛 이름은 PGR·JPM·CME·V 확장 전용이었다 |
| **R6 보완(사용자 요청):** `test_state_write_boundary.py`가 고정이 풀리는 `test_manual_portfolio_analysis.py`에서 도우미 7개를 import하던 것을, 원본 소스 그대로 이 고정 파일 안으로 옮겼다 | 고정 테스트가 고정 밖 코드에 기대지 않게. 옮긴 상수 4·함수 5가 원본과 AST 단위로 같고, 이 파일은 이제 어떤 `test_*` 모듈도 import하지 않는다. 결과도 같다(옮기기 전·후 3건 모두 ok). 고정 파일이 바뀌므로 첫 R7 후보 `2913241f…`는 무효가 되어 커밋하지 않고 폐기했다(§4) |

## 4. R7

### 4-1. 첫 후보 (폐기, 커밋 안 함)

- `2913241f95b1…`(기준 커밋 `e42f9db`)이다.
- materialize와 후보 검증기는 PASS였다.
- 사용자 요청으로 고정 파일 `test_state_write_boundary.py`를 고쳤기 때문에 구현 해시가 맞지 않게 됐다. 그래서 worktree와 복사본에서 지웠다.
- 이 후보로 한 모의 활성화 결과는 §4-3에 남긴다. 새 후보로 다시 확인했다.

### 4-2. 다시 만든 후보 (커밋 `48798d1` 기준, `origcopy`)

- 복사본의 `manage-us-stock-strategy/` 528개 파일이 커밋 `48798d1`과 같음을 확인했다(줄바꿈 정규화 비교, 누락·불일치 0).
- 사전 점검: 같은 입력으로 메모리에서만 만들어 SHA를 확인한 뒤, 실제 생성은 1회만 했다.
- 후보: `workspace/research/provider-evidence/kiwoom/2026-10-05/45cf188892601d61c117519b4d34fc9e6b2ee82074489b8dd9cc0b661ca8bc80/session-aware-priority-acceptance-inactive-superseding-candidate.json`
  - 생성 시각 `2026-10-05T09:50:10+09:00`, `repository_base_commit` `48798d1830df212e777eda3accb3ddf1e587be57`
  - `supersedes` `f0bab…`, 15종목(활성 정책 순서), 고정 경로 27개, pin-scope `I4-R6-20261005`
  - provider scope 정책 정규화 해시 `a3d2ae10…`
  - 드리프트 6개(manifest 스키마, runtime bridge, materialize, 후보 검증기, `run_manual`, `test_manual`)가 허용 목록 6개와 정확히 같다
  - 권한: `activation_performed=false`, `order_authority=false`, `quantity_authority=none`, `execution_quantity=null`
- materialize 결과 `PASS`(`write_status` `CREATED`). 후보 검증기 CLI `PASS`(오류 0).
- worktree로 바이트 그대로 옮겼다(SHA 일치, LF, BOM 없음).

### 4-3. 모의 활성화 (복사본에서만)

- **실제 정책 파일은 고치지 않았다.**
  - 모의 활성화는 `origcopy`를 다시 복사한 `simcopy` 안의 정책 2개에서만 했다.
  - 원본 폴더 정책에는 `f0bab…`가 그대로 16+1곳 있고, 후보 해시는 0곳이다. 원본 폴더의 정책·상태 status는 0줄이다.
  - worktree의 `5dd739f` 대비 `workspace/policies`·`workspace/state`·`stock-strategy-system` diff는 0이다.
- 바꾼 곳: priority policy 소문자 15곳·대문자 1곳, source_capabilities 대문자 1곳. 바뀐 뒤 `f0bab` 잔여는 0이다.
- 첫 후보로 한 결과:

  | 확인 | 결과 |
  |---|---|
  | 운영 검증기 `validate_kiwoom_session_aware_acceptance.py`(후보 기준) | PASS, 오류 0 |
  | v2_6_7 acceptance 2건 | **해소** |
  | materialize 24건 | 활성화 뒤에도 통과(R9 뒤에도 깨지지 않음) |
  | 전체 테스트 | `Ran 2451` / failures 8, errors 1. 같은 실패 8건(환경·상태 의존), 해소 2건, **새 실패 1건** |
  | 새 실패 | `test_provider_authority_change_starts_zero_count_cohort`. `shadow_progress.json`에 저장된 지문 `628c6081…` ≠ 재계산 지문 `20eda27a…`. 지문 재료 중 바뀐 파일은 활성화가 고치는 정책 2개뿐이다(alert_policy·등록부·route 부분은 같음). → R9 활성화에는 새 0회 cohort 시작(상태 파일 이관과 보관 파일 1개)이 반드시 함께 필요하다(§7-1) |

- 새 후보 `45cf1888…`로 다시 한 결과:
  - `simcopy`를 `origcopy`(커밋 `48798d1` + 새 후보)에서 새로 복사했다.
  - 같은 17곳을 `45cf1888…`로 바꿨다. 소문자 15·대문자 1, 대문자 1. 바뀐 뒤 `f0bab` 잔여는 0이다.

  | 확인 | 결과 |
  |---|---|
  | 운영 검증기(후보 기준) | PASS, 오류 0 |
  | v2_6_7 acceptance 2건 | **해소** |
  | materialize 24건 | 통과 |
  | 전체 테스트 | `Ran 2452` / failures 8, errors 1. 같은 실패 8건, 해소 2건, 예상한 새 실패 1건(cohort 지문, 저장 `628c6081…` ≠ 재계산 `4f11526e…`), **그 밖의 새 실패 0** |

  - `simcopy`와 `origcopy`는 정책 2개만 다르다. 그래서 지문이 바뀐 원인도 그 두 파일이다. 재계산 값이 첫 시뮬레이션(`20eda27a…`)과 다른 것은 후보 해시가 달라졌기 때문이다.

## 5. 이전 테스트 → 새 테스트 대응표

### 5-1. 옮긴 보호 기능 (이전 테스트는 `test_manual_portfolio_analysis.py`에 그대로 남아 있고 모두 통과)

| 보호 기능 | 이전 테스트 | 새 테스트(고정) | 강도 | 원본과 다른 점 |
|---|---|---|---|---|
| 가격 부호 `_cur_prc_price` | `test_07i1`, `test_07i2`(`_current_price_record` 경유) | `test_manual_data_guards.PriceSignGuardTest` 2건 | 같은 사례 + `None`·bool | 없음(소스 동일) |
| `_number` | `test_07i3` | `test_generic_positive_number_behavior_is_unchanged` | 같은 3단언 + 6사례 | 없음 |
| 시간대 `_timestamp` | `test_02r`(간접) | `TimestampGuardTest` 3건 | 직접 검사 추가 | 없음 |
| temporal(cutoff·valid) | `test_02p`, `02q`, `02v` | `TemporalGuardTest` 4건 | 같은 단언 + 누락·형식 오류 | 없음 |
| `compare_broker_and_system` | `test_03`, `test_invalid_broker_keeps_history…`(보고서 경유) | `BrokerComparisonGuardTest` 4건 | 차이 3종, UNKNOWN 경로 직접 검사 | 없음 |
| `_normalize_broker_state` | `test_k2_*`, `test_s1b_*`, `test_kiwoom_broker_shadow`(`run_manual` 이름으로 import, 그대로 통과) | `BrokerNormalizationFailClosedTest` 3건, 위임 테스트 1건 | ⑧ 추가 | ⑧ 분기 추가. **`acquisition_cutoff` 인자 신설**(§5-3) |
| `validate_scheduled_input` | `ScheduledRegisteredTaskBindingTests` t1·t8·grade_b, `ScheduledInputRunnerTests` | `test_scheduled_input_gate` 8건 | 게이트 직접 호출 + wrapper 위임 + 형식 거부 + deriver 실패 + 유일 호출자·정본 deriver AST 단언 | **`provenance_deriver` 인자 신설**(§5-3). 본문은 `derive_run_provenance(run, policy)` → `provenance_deriver(run, policy)` 한 줄만 다름 |
| 재수출 동일성 | — | `ManualAdapterUsesPinnedGuardsTest` | 새 단언 | — |
| 경계 test_04 | `test_04`(유지) | `test_state_write_boundary.test_04` | 같은 단언 + `write_bytes`·`unlink`·`rename` 감시 + 스키마 | — |
| 경계 test_08 | `test_08`(유지) | `test_state_write_boundary.test_08` | 같은 단언 + 금지 모듈 2개(`reconcile_broker_state`, `portfolio_review_journal`) + 고정 모듈 2개 AST | — |
| ⑧ 보고서 수준 | — | `test_normalization_failure_hard_fails…` | 새 단언 | — |

### 5-2. materialize 테스트 (사용자 승인한 재작성)

| 이전 | 새 | 증명하는 내용 |
|---|---|---|
| 01 정확한 15종목·비활성 | 01 | 종목 = 활성 정책 순서(15), 권한 3필드, 옛 원시 블록 없음 |
| 02 provider scope 원시 해시 `9604…` | 02 | 정책 정규화 해시가 계약·바인딩에 같은 값으로 들어감 |
| 03 결정적 바이트 | 03 | 같음 |
| 03a 16개 정규화 해시 | 03a | pin-scope 27개와 같은 집합, 해제 파일 없음, pin-scope 자기 고정 |
| 03b CRLF·LF·BOM | 03b | 바꾸지 않음 |
| 04 ID 상이(`2994…` 하드코딩) | 04 | 정책 바인딩으로 찾은 활성 ID와 다름, 바인딩 일치 |
| 05 검증기 PASS | 05 | 같음 + 원시 = 정규화 = 폴더 이름 |
| 06·07·08 중복·형식 오류·제외 종목 | 06·07·08 | 같음 |
| 09 원시 바인딩 불일치 | 09 | 정규화 바인딩 불일치 |
| 09a 원시 해시만 쓴 구현 바인딩 | 09a | CRLF 원시 해시를 넣으면 FAIL(이전에는 CRLF 파일이 있어야만 실행됐음, 이제 항상 실행) |
| 09b 운영 검증기 투영 | 09b | 같음(27개) |
| 10 활성 acceptance 유효 | 10 | 활성 오류 = 허용된 드리프트뿐, 기록 = 계산 |
| 11 정본 경로 밖 거부 | 11 | 같음 |
| — | 12~20 (합성 선행) | 허용 드리프트 기록·검증 PASS / 허용 밖 드리프트 FAIL / 다른 선행에 묶인 허용 FAIL / 해시 아닌 오류 FAIL / 순서 바뀐 범위 FAIL / 갈라진 바인딩 FAIL / pin-scope 자기 고정 누락 FAIL / 검증기가 조작된 기록·옛 블록·줄인 집합·넓힌 범위·권한 변경 FAIL / 허용 밖 드리프트는 기록이 맞아도 FAIL |

### 5-3. 고정 함수에 생긴 주입 인자와 우회 가능성 판단

**`scheduled_input_gate.validate_scheduled_input(..., provenance_deriver=derive_run_provenance)`**
- **원본과 다른 점:** 원본(`run_manual`, `5dd739f`)은 모듈 이름 `derive_run_provenance`를 직접 불렀다. 옮긴 게이트는 이 함수를 인자로 받는다. 기본값은 정본인 `continuous_improvement_sidecar.derive_run_provenance`다.
- **운영 경로에서는 우회할 수 없다.**
  - 유일한 운영 호출자는 `portfolio_decision_dashboard.py:1426-1432`이고, `run_manual.validate_scheduled_input`(wrapper)을 부른다.
  - wrapper 시그니처에는 deriver 인자가 없다. wrapper는 항상 자기 모듈의 `derive_run_provenance`를 넘긴다. CLI 인자로도 노출되지 않는다.
  - 고정 테스트 `test_adapter_name_is_a_thin_delegate_to_the_pinned_gate`가 wrapper가 넘기는 값이 정본 함수 객체인지 단언한다.
- **직접 호출하면 한 검사를 끌 수 있다.**
  - `scripts/` 안에서 `scheduled_input_gate`를 import하는 파일은 지금 `run_manual` 하나뿐이다.
  - 누군가 게이트를 직접 import해서 느슨한 deriver를 넘기면, `SCHEDULED_CANONICAL_PROVENANCE_NOT_VERIFIED` 재도출 검사 1개를 건너뛸 수 있다.
  - 나머지 검사는 그대로 남는다: 배포 검증(`verify_current_provenance`, 등록 작업 설정 포함), 증거 모드·바인딩, 공식 세션 일정, temporal, 포트폴리오 해시, 원천 증거 해시, 보고서 provenance 필드.
- **선례:** 원본에도 같은 성질의 주입 인자 `session_authority_resolver`가 있었다(dashboard가 자기 resolver를 넘긴다).
- **판단:** 같은 프로세스 안에서 호출 코드를 쓸 수 있는 쪽만 가능한 좁은 우회다. 운영 호출 경로에는 열려 있지 않다. 다만 고정 모듈의 검사 하나를 호출자가 끌 수 있는 구조인 것은 사실이다.
- **보강(사용자 결정 (나), R6 보완 `48798d1`에 반영):** 고정 테스트 `test_only_the_adapter_reaches_the_gate_and_only_with_the_canonical_deriver`를 추가했다. 단언하는 것은 다음과 같다.
  - `scripts/`에서 `scheduled_input_gate`를 import하는 파일은 `run_manual` 하나뿐이다.
  - 그 안의 게이트 호출은 하나이고 `provenance_deriver=derive_run_provenance`(이름 그대로)만 넘긴다.
  - `derive_run_provenance`는 `continuous_improvement_sidecar`에서 별칭 없이 import한다.
  - 모듈 안에서 이 이름을 다시 정의하거나 대입하지 않는다.
- **변이 검사(복사본에서만):**
  - deriver를 lambda로 바꾸면 FAIL이다(`ast.Lambda`는 `ast.Name`이 아님).
  - 게이트를 직접 import하는 스크립트를 더하면 FAIL이다.
  - 원복하면 OK다.
- **버린 안:**
  - (가) 문서만 남기기.
  - (다) 인자 제거. 기존 t8 단언이 빈 단언이 되기 때문이다.

**`manual_data_guards.normalize_broker_state(..., acquisition_cutoff=_acquisition_complete_cutoff)`**
- 원본은 `_acquisition_complete_cutoff`를 직접 불렀다. 기존 테스트가 `run_manual._acquisition_complete_cutoff`를 patch하므로, wrapper가 그 이름을 넘기는 seam을 만들었다.
- 이 인자가 바꾸는 것은 broker `as_of` 시각뿐이다. 상태(`AVAILABLE`/`UNAVAILABLE`), 보유, 현금, ⑧ 판정에는 영향이 없다.
- 운영 호출자는 `run_manual` wrapper 하나다.

## 6. 검증

### 6-1. 전체 테스트 (`origcopy`, 활성화 전)

| 코드 | 결과 |
|---|---|
| R6 `e42f9db` | `Ran 2451`(새 테스트 52건) / failures 9, errors 1. **새 실패 0**, 해소 materialize 15건 |
| R6 보완 `48798d1` | `Ran 2452`(게이트 AST 단언 +1) / failures 9, errors 1. 위와 같은 10건, **새 실패 0** |

- 남은 실패는 두 묶음이다.
  - 환경·상태 의존 8건: 기준선과 같은 테스트, 같은 원인.
  - v2_6_7 2건: R9 전에는 원리상 해소할 수 없다. §4-3에서 모의 활성화로 해소를 확인했다.
- v2_6_7 2건의 불일치 6개: 로그에는 unittest가 목록을 잘라 첫 파일만 보인다. Builder가 `predecessor_implementation_drift` 계산으로 6개 이름을 모두 확인했고, pin-scope 허용 목록 6개와 같다.

### 6-2. 부록 A7 5번 대상 테스트 (`origcopy`, 기준선도 모두 실패 0)

| 테스트 | 기준선 | R6 뒤 |
|---|---|---|
| `test_reconcile_broker_state` | 실패 0 | 56건 OK |
| `test_cash_flow_evidence` | 실패 0 | 19건 OK |
| `test_cash_flow_evidence_u3` | 실패 0 | 18건 OK |
| `test_s1b_provider_marks` | 실패 0 | 20건 OK |
| `test_s1b_plan_b_no_data_pass` | 실패 0 | 28건 OK |
| `test_k2_bridge_evidence_integrity` | 실패 0 | 18건 OK |
| `test_decision_journal_cards` | 실패 0 | 30건 OK |
| `test_portfolio_review_journal` | 실패 0 | 9건 OK |
| 옮긴 test_04·test_08(기존 위치) | 통과 | `test_manual_portfolio_analysis`의 `test_04`, `test_08` OK |
| 옮긴 test_04·test_08(고정 새 위치) | — | `test_state_write_boundary` 3건 OK(R6 보완 전·후 같음) |

- 기준선 열은 기준선 전체 실행의 실패 목록에 이 파일들이 없었다는 뜻이다. 테스트 파일 자체는 R6에서 바뀌지 않았다(`test_state_write_boundary` 제외).

### 6-3. 그 밖

| 확인 | 결과 |
|---|---|
| `test_manual_portfolio_analysis` | 115건 통과(기준선과 같음) |
| 스키마 감사, ASCII 규칙 | PASS, PASS |
| 금지 파일 diff | 0 |
| ⑦ dirty 판정(autocrlf=true, 줄바꿈 혼재) | 원본 폴더·worktree 모두 코드 범위 status 0줄(줄바꿈 차이를 dirty로 보지 않음) |

## 7. R9와 이후로 넘기는 것 (확인 필요 포함)

1. **R9에는 shadow cohort 이관이 필수다(상태 파일, 사용자 승인).**
   - 정책 2개를 바꾸면 통합 shadow 지문이 바뀐다(§4-3). 그러면 `workspace/state/integrated_shadow/shadow_progress.json`을 `migrate_integrated_shadow_cohort.py`로 새 0회 cohort로 옮겨야 `test_v2_6_7`의 cohort 테스트가 통과한다.
   - S7 2차 X15도 같은 이관이 필요하다(옛 통제 은퇴로 `holding_risk_rules`·`holding_timing_rules`가 바뀜).
   - 둘을 따로 하면 이관이 두 번이 된다. **R9와 S7 2차의 순서, 또는 한 번에 묶을지는 결정이 필요하다.** 지금은 카운터가 0이라 잃는 기록은 없다(S7 보고 1a).
2. **R9 활성화 범위.**
   - priority policy: `provider_scopes` 15행 + `acceptance_evidence` 1곳(대문자). source_capabilities: `kiwoom_rest` 1곳(대문자). 모두 새 후보 해시로 바꾼다.
   - 여기에 위 1의 cohort 이관과, `CLAUDE.md` Change classes의 "run_manual 편집 = K3" 문구 교체가 더해진다(고정 목록은 pin-scope asset).
   - 후보 바이트(LF, BOM 없음)는 그대로 둔다. 그래야 원시 해시 = 정규화 해시다.
3. **⑥ 범위를 줄인 데서 남은 한계.**
   - `test_v2_6_7`의 helper는 여전히 원시 바이트로 현재 acceptance를 찾는다. 그래서 worktree·새 clone(autocrlf=true)에서는 acceptance 테스트를 판정할 수 없다.
   - R8 Judge도 바이트 복사본에서 판정해야 한다.
   - `.gitattributes` 또는 helper 정규화는 별도 결정 사항이다.
4. **고정 테스트의 fixture 의존(일부 해소).**
   - `test_state_write_boundary`: R6 보완으로 해소. 고정 밖 `test_*` 모듈을 import하지 않는다.
   - `test_scheduled_input_gate`: 아직 `test_portfolio_decision_dashboard`(`scheduled_compilation_fixture`, `bind_scheduled_fixture`)와 `test_deployment_provenance`(`fixture_git`, `supply_task_config`)를 import한다.
     - `scheduled_compilation_fixture`는 40줄이지만 같은 모듈의 `session_k3_inputs`·`current_context`·`evidence_raw_bytes` 등을 연쇄 호출한다. 옮기려면 규모가 크다.
     - 이 fixture를 약하게 바꾸면 고정 해시는 그대로인데 게이트 테스트 5건의 힘이 줄 수 있다.
     - 처리 방법은 결정이 필요하다. fixture 없이 도는 게이트 테스트 2건은 영향이 없다.
   - 두 고정 테스트 모두 시험 대상인 `run_manual`(고정 해제됨)을 import한다. 이것은 "해제된 어댑터가 고정 guard를 계속 쓰는가"를 확인하는 의도된 의존이다.
5. **고정 모듈이 고정 밖 모듈에 기댄다.**
   - `reconcile_broker_state.py`는 적용 직후 검사에서 `evaluate_alerts.leveraged_state_integrity_errors`를 지연 import한다. 이 파일은 S7 2차가 고친다.
   - 공용 helper도 고정하지 않았다: `validation_common`, `kiwoom_adapter_io`, `provider_resilience`, `resolve_kiwoom_us_instrument`, `authority_artifact_io`, `validate_source_capabilities`, `continuous_improvement_sidecar`, `session_authority`, 그리고 정규화 해시 함수가 있는 `validate_skill_deployment`. 16개 체계 때도 고정 대상이 아니었다.
6. **⑦ dirty 판정은 LF로 체크아웃하는 Linux CI에서의 동작이 확인 필요다.**
7. **⑤가 함께 바꾸는 것.** `kiwoom_candidate_discovery_bridge`도 `return_code` 누락·bool·null을 실패로 본다. 명세상 이 필드가 빠지는 사례는 없지만, 라이브 응답으로는 확인하지 않았다.
8. **범위 밖 종목(2e, 추가하지 않음).** MU, DELL, AMD, TQQQ, DRAM, PWR, LITE, SPY. 키움 시세 범위에 넣으려면 새 acceptance 증거가 필요한 범위 확장이다(P4 §5 SPY 항목, S7 X14).
9. **원천 증거 9개.** 후보는 미추적 `workspace/outputs/activation/…` 9개를 원시 해시로 그대로 참조한다. 후보 검증기는 이 파일들이 있어야 PASS한다(원본 폴더와 복사본에는 있음, worktree에는 없음).
10. **R7 후보를 두 번 생성했다.** 첫 후보는 커밋 전에 폐기했다(§4-1). A7의 "1회 생성"과 다르다.

## 8. Judge(R8)가 볼 곳

- **판정 위치를 재현하는 방법**
  - 원본 폴더를 `.claude`·`.runtime-cache`만 빼고 바이트 그대로 복사한다(`robocopy /E /COPY:DT`).
  - `git -C <copy> fetch <원본> worktree-gov-r6`으로 커밋을 가져온 뒤, `manage-us-stock-strategy/` 파일을 마지막 R6 커밋 내용으로 맞춘다.
  - Builder는 동기화 뒤 파일이 커밋과 같음을 줄바꿈 정규화 비교로 확인했다.
  - 모의 활성화는 그 복사본의 복사본에서 §4-3의 17곳을 바꿔 재현한다.
- **설계 판단**: §3-3(드리프트 허용), §5-3(주입 인자 두 개).
- **코드**
  - `manual_data_guards.py`: ⑧ 분기, `acquisition_cutoff`. 옮긴 10개 함수는 원본 `5dd739f`와 AST 소스가 같다.
  - `scheduled_input_gate.py`: `provenance_deriver`.
  - `run_manual_portfolio_analysis.py`: wrapper 2개, ⑧ hard fail, ⑦.
  - `validate_kiwoom_session_aware_acceptance_candidate.py`: `_validate_candidate_v12`, `allowed_drift_for`, `disallowed_predecessor_errors`.
  - materialize: 활성 탐색, 허용 드리프트 판정.
  - `kiwoom_runtime_bridge.py`: `_return_code_ok`와 `_request`·`_fetch_page`의 누락 분기.
- **데이터**
  - `assets/kiwoom-acceptance-pin-scope.json`의 27개 목록과 허용 드리프트 6개가 승인된 2a·실제 드리프트와 같은지.
  - 후보의 범위 = 기존 15종목, 권한 3필드.
- **테스트**: §5 대응표. 특히 materialize `test_10`의 의미 변경("활성 유효" → "허용 드리프트 외 유효")과 12~20의 합성 선행.
- **기존 8단계 범위**: `a5e872a` fail-closed 변경(이번에 바꾸지 않음), 08-13/14 증거 재사용의 적정성(사용자 결정 2d).

## 9. 실행 위치와 남긴 파일

- 판정용 복사본 `origcopy`·`simcopy`와 로그(`baseline-full.log`, `after-r6-full.log`, `sim-activation-full.log`, 실패 요약 md)는 세션 scratchpad에 있고, 저장소 밖이다.
- 저장소에서 만든 파일은 R6 커밋 파일, R6 보완 1개, R7 후보 1개, 이 보고서뿐이다.

fail-open 6종(Partial·Stale·Missing·Unknown·Deny-list·Swallowed)을 새 결정 경로마다 대어 봤다: 예.
- 드리프트 허용: 부분 기록은 기록 = 계산 비교로 FAIL. 다른 선행에 묶인(Stale) 허용은 0개 허용. 구현·pin-scope·스키마가 없으면 FAIL. 활성 manifest를 0개 또는 2개 찾으면 FAIL. 허용은 경로 allow-list이고 해시 아닌 오류는 전부 FAIL. 읽기 실패 파일은 건너뛰지만, 그 결과 활성을 못 찾으면 FAIL.
- `return_code`: 누락·`null`·bool은 FAIL.
- ⑧: 삼켜지던 예외가 이제 `UNAVAILABLE`과 hard fail이 된다.
- ⑦: git을 읽지 못하거나 일부 명령만 실패하면 `UNAVAILABLE`이고, CLEAN으로 보지 않는다.
- 주입 인자(§5-3): 운영 경로에서는 정본 함수만 넘어간다. 직접 호출자만 deriver 검사 1개를 끌 수 있다(Unknown 아님, 결정 필요로 남김).
