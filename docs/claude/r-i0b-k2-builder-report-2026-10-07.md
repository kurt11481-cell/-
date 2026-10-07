# r-i0b-k2 대시보드 타이밍 테스트 픽스처 — Builder 보고 (2026-10-07, K2)

- 지시문: `docs/claude/r-i0b-k2-builder-prompt-2026-10-07.md` 2절.
- worktree는 `i0b-k2-tests`이고 HEAD는 `0827f42`입니다. 기준 `782ee27`에 지시문 문서 1개를 더한 커밋입니다. 커밋 전 상태입니다.
- 근거: 설계 `i0b-fill-confirmation-design-2026-10-06.md` §11(Judge 비차단 권고 ②③④), 이전 Builder 보고 `i0b-policy-builder-report-2026-10-06.md` §2-2, §3-5, §6-2.
- 소비자(다음에 이 보고서를 읽는 곳):
  - Cowork 읽기 확인(지시문 3절)
  - 관제판 `r-i0b-k2`
  - S7 2차(`p-s7-p2`) 착수 전 회귀 기준선

## 0. 결론

- 대시보드 타이밍 테스트 묶음이 이제 실제 정책·실제 상태 보유에 묶이지 않고 합성 타이밍 블록으로 돕니다. 묶음은 `ManualStep2TimingTests`와 이를 쓰는 8개 클래스입니다.
- 바이트 사본 기준 결과:
  - 대상 모듈: 해소 139, 새 실패 0
  - 전체 스위트: 해소 139, 새 실패 0
- T2에 0주 분기 단언을, T1에 `all_required_evidence_verified` 단언을 넣었습니다.
- 바뀐 파일은 테스트 2개와 이 보고서뿐입니다. 정책·상태·scripts diff는 0입니다.
- 지시문과 다른 사실이 두 가지 있습니다.
  - worktree의 `INTEGRITY_FAILURE` 원인은 `portfolio_state.json`이 없어서가 아니라 artifact 줄바꿈 변환입니다(1-1).
  - 실제 상태의 NBIS가 13주로 바뀌어 있었습니다(1-4). NBIS 처리는 사용자 승인을 받았습니다.

## 1. 원인 확인 (1단계)

### 1-1. worktree `INTEGRITY_FAILURE`의 원인

- `stock-strategy-system/portfolio_state.json`은 worktree에 이미 있습니다. `.worktreeinclude`(커밋 `6a5a167`, 2026-09-30)가 복사한 것이고, 본 폴더와 sha256이 같습니다(`fbb7808c…`). 따라서 상태 파일은 원인이 아니고 복사도 필요 없었습니다.
- 실제 원인은 `core.autocrlf=true`입니다.
  - 내용주소 artifact 13개(`workspace/calendar-authority/artifacts/*`, `workspace/instrument-identity-authority/artifacts/*`)는 저장소에 `i/lf`로 들어 있습니다. worktree에는 `w/crlf`로 체크아웃됩니다.
  - 예: `a8a3aef2…/us-equities-core-session-v2.calendar.json`의 HEAD blob은 `a8a3…`(24364바이트)입니다. worktree 사본은 `dd35dc6b…`(24365바이트)입니다.
  - 본 폴더 사본은 `a8a3…`로 디렉터리 이름과 같습니다.
- 해시가 다르면 `integrated_authority_snapshot._read_session_artifact`(196행)가 `INTEGRITY_FAILURE`를 냅니다. 테스트 픽스처 `_copy_artifacts`(`test_integrated_authority_snapshot.py:56`)가 이 파일을 그대로 복사하기 때문입니다.
- 그래서 타이밍과 무관한 `ScheduledCompilationTests`와 `SessionK3DashboardBoundaryTests`도 worktree에서 같은 이유로 실패합니다.

### 1-2. 실제 정책·상태를 읽는 경로

- `ManualStep2TimingTests.setUp`이 `EvaluateTimingIntegrationTests.setUp`을 부릅니다. 그 setUp은 `SYSTEM_ROOT/alert_policy.json`(positions `{}`)과 `SYSTEM_ROOT/portfolio_state.json`(revision 20)을 읽습니다.
- 여기서 나온 `case.policy`·`case.state`가 다음 세 곳에 들어갑니다.
  - `self.inputs`
  - 임시 폴더의 `state.json`·`policy.json`. `dashboard.DEFAULT_PORTFOLIO_STATE`·`DEFAULT_ALERT_POLICY`를 patch합니다.
  - Kiwoom 캡처 픽스처 `account_reader_for(state["holdings"], …)`. 브로커 보유가 여기서 만들어집니다.
- 실제 값은 MVLL 278(anchor 396과 다름), SOXL 75(= 99 − R25 24), NBIS 13입니다. 정책에 타이밍 positions가 없어서 `VERIFIED_REDUCTION_REVIEW`가 나올 수 없었습니다.

### 1-3. 클래스 수 (기존 보고서의 "7개 클래스 약 150건"과의 차이)

| 클래스 | 관계 | 테스트(subtest 포함 결과 줄) |
|---|---|---|
| ManualStep2TimingTests | 기반 | 12 |
| ManualCliInputWiringTests | 직접 | 9 |
| TechnicalTimingConsumerAlignmentTests | 직접 | 7 |
| ManualKiwoomCaptureCliTests | ManualCliInputWiringTests를 거침 (**기존 보고서에 없음**) | 2 |
| ManualTimingBrokerInputTests | TechnicalTimingConsumerAlignmentTests를 거침 | 6 |
| BrokerCurrentStateAlignmentTests | TechnicalTimingConsumerAlignmentTests를 거침 | 4 |
| ManualKiwoomOnlyTimingTests | TechnicalTimingConsumerAlignmentTests를 거침 | 25 |
| ManualCorporateActionClearanceTests | ManualKiwoomOnlyTimingTests 하위 클래스 | 46 |
| ManualTimingEvidenceContractTests | ManualCorporateActionClearanceTests 하위 클래스 | 52 |

- ManualStep2TimingTests를 쓰는 클래스는 8개이고, 묶음 전체는 163건입니다.
- worktree에서는 이 가운데 144건이 실패합니다(실패 4 + 오류 140).
- 바이트 사본에서는 139건이 실패합니다(subtest를 따로 세면 실패 결과 줄은 139). Judge가 말한 "알려진 실패 139건"과 같습니다.
- CLI 두 클래스(11건)는 변경 전에도 통과했습니다.

### 1-4. 지시문에 없던 사실: NBIS

- 실제 상태가 이제 NBIS 13주입니다.
- 네 곳은 "실제 상태 NBIS 15, 브로커 13"으로 불일치를 만듭니다. `holdings_change=("NBIS", 13)`을 쓰는 곳으로, 대상은 다음과 같습니다.
  - `TechnicalTimingConsumerAlignmentTests.test_unrelated_broker_mismatch…`
  - `ManualTimingBrokerInputTests.test_actual_broker_facts…`
  - `BrokerCurrentStateAlignmentTests.test_current_nbis_quantity…`
  - `ManualKiwoomOnlyTimingTests`의 3106행 경로
- 바이트 사본 기준선에서는 `13 != 15`와 `NOT_VERIFIED` 실패로 나타났습니다.
- 사용자 결정(2026-10-07): 메모리 NBIS도 합성값 15주로 맞춘다. 원가는 기존 정규화대로 평균 100, 합계 1500입니다.

## 2. 변경 (2단계)

| 파일 | 바꾼 것 |
|---|---|
| `tests/test_portfolio_decision_dashboard.py` `ManualStep2TimingTests.setUp` | `case.policy = with_timing_positions(case.policy, "MVLL", "SOXL")`. 합성 positions의 각 종목 메모리 보유를 "state anchor − 완료 트랜치 수량"으로 맞춤(MVLL 396, SOXL 75). 메모리 NBIS 15, 평균 원가 100.0, 원가 합계 1500.0. 파일 쓰기 없음(기존 임시 파일 경로 그대로) |
| 같은 파일 `test_stale_internal_timing_quantity_does_not_override_valid_broker_and_anchor` | **바꾸지 않음.** 브로커 MVLL은 setUp의 메모리 보유 396으로 만들어지고, 테스트가 내부 상태만 395로 바꿉니다. 그래서 "Broker=396; approved anchor=396"이 같은 뜻으로 성립합니다. 바이트 사본에서 변경 전 실패, 변경 후 통과 |
| `tests/test_evaluate_timing_integration.py` T2 | 0주 분기 추가: 메모리 NBIS 0 → `STATE_MISMATCH`/F, 경고 `"holding-risk policy symbols are not positive verified holdings: NBIS"`(`evaluate_alerts.py:511-516`의 `set(positions) - positive_holdings`, 745행에서 F) |
| 같은 파일 T1 | `active[0]["evidence_verification"]["all_required_evidence_verified"]` True 단언 복원. 지시문의 `result[...]`가 아니라 후보 안 증거 레코드입니다(`evaluate_alerts.py:623`, 913행 타이밍 후보 경로). 6bd5c5a에서 지운 단언과 같은 형태 |

- `scripts/`는 읽기만 했습니다. 코드를 고쳐야만 통과하는 항목은 없었습니다.
- 두 파일 모두 CRLF를 유지했습니다(변경 후 4188/4188줄, 347/347줄).

## 3. 테스트 (3단계)

### 3-1. 환경

- **worktree**: 그대로 실행했습니다. artifact가 CRLF여서 `INTEGRITY_FAILURE`가 납니다.
- **바이트 사본**(사용자 승인 방식):
  - 스크래치패드에 `.git`을 뺀 worktree 사본을 만들었습니다(`make_byte_copy.py`).
  - artifact 13개만 HEAD blob(LF) 바이트로 바꿨습니다. 13개 모두 sha256이 디렉터리 이름과 같습니다.
  - `fs_before`/`full_before`는 대상 테스트 2개를 HEAD blob으로 둔 사본입니다. blob 해시 `c0388e3a…`, `e12f64cc…`가 일치하고, 두 사본의 차이는 이 2개 파일뿐입니다.
  - 상태 파일 sha256은 실행 전후 모두 `fbb7808c…`입니다.
  - worktree와 본 폴더는 건드리지 않았습니다.

### 3-2. 대상 모듈 (기준선 대비)

| 환경 | 모듈 | 실행 | 실패+오류 전 → 후 | 새 실패 | 해소 |
|---|---|---|---|---|---|
| worktree | test_portfolio_decision_dashboard | 306 | 5+187 → 1+187 | 0 | 4(ManualStep2TimingTests) |
| worktree | test_evaluate_timing_integration | 14 | 0 → 0 | 0 | 0 |
| 바이트 사본 | test_portfolio_decision_dashboard | 306 | 134+6 → 1+0 | 0 | 139 |
| 바이트 사본 | test_evaluate_timing_integration | 14 | 0 → 0 | 0 | 0 |

- 바이트 사본에서 해소된 139건(클래스별):

| 클래스 | 건수 |
|---|---|
| ManualTimingEvidenceContractTests | 48 |
| ManualCorporateActionClearanceTests | 41 |
| ManualKiwoomOnlyTimingTests | 36 |
| ManualStep2TimingTests | 4 |
| TechnicalTimingConsumerAlignmentTests | 4 |
| BrokerCurrentStateAlignmentTests | 3 |
| ManualTimingBrokerInputTests | 3 |

- 바이트 사본의 변경 전 실패 메시지는 상태·정책 원인이었습니다. 주로 `'NOT_VERIFIED' != 'VERIFIED_REDUCTION_REVIEW'`, `KeyError: 'holding_timing_evidence'`, `13 != 15`, `False is not true`입니다.
- 두 환경에 함께 남는 1건은 `PortfolioDecisionDashboardTests.test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan`("False is not true")입니다. 변경 전후 메시지가 같고, 원인은 분석하지 않았습니다(이전 보고서 §6-8과 같음).
- worktree에 남는 오류 187건은 모두 `IntegratedAuthorityLoadError: INTEGRITY_FAILURE`(1-1, 환경 원인)입니다.
  - 타이밍 묶음 140
  - ScheduledCompilationTests 25(subtest)
  - SessionK3DashboardBoundaryTests 22(subtest)
  - 앞의 140건은 바이트 사본에서는 통과합니다.

### 3-3. 전체 스위트 (서브에이전트 1회, 바이트 사본)

| 사본 | 실행 | 실패 | 오류 | 건너뜀 |
|---|---|---|---|---|
| full_before | 2492 | 159 | 17 | 4 |
| full_after | 2492 | 26 | 11 | 4 |

- **새 실패: 0.** 해소 139건은 3-2와 같은 id입니다.
- 공통 실패 37건은 두 사본에서 id와 메시지가 같습니다(메시지가 바뀐 것 0). 전부 이번 변경과 무관합니다.

| 묶음 | 건수 |
|---|---|
| "current Acceptance binding must resolve to exactly one manifest: binding=835d4f46…"(사본에 acceptance manifest 없음) | 14 |
| GitignoreTests `False is not true`(사본에 `.git` 없음) | 8 |
| 사본에 없는 산출물 `FileNotFoundError` | 8 |
| `git ls-files` 128(`.git` 없음) | 2 |
| grade_b 픽스처(3-2) | 1 |
| ConfirmationIdentityCandidateTest, InstrumentIdentityAuthorityTest, KiwoomAcceptanceCandidateMaterializationTest, SyntheticPredecessorDriftTest | 각 1 |

- 결과 파일은 스크래치패드(저장소 밖)에 있습니다: `full_before.txt`, `full_after.txt`, `fsb_dash.txt`, `fsa_dash.txt`, `dash_before.txt`, `dash_after.txt`, `compare.py`.

### 3-4. 스키마 감사

- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py` → `{"status": "PASS", "errors": []}`.

## 4. 경계 (4단계)

| 확인 | 결과 |
|---|---|
| `git status --short` | ` M` 테스트 2개(`test_evaluate_timing_integration.py`, `test_portfolio_decision_dashboard.py`)와 새 파일 이 보고서 |
| `git diff --stat` | 2 files changed, 27 insertions(+), 7 deletions(-) |
| `git diff -- scripts stock-strategy-system workspace assets schemas` | 0줄 |
| pin 목록(`kiwoom-acceptance-pin-scope.json` `required_implementation_paths` 27개) | 바꾼 테스트 2개는 목록에 없음(목록의 테스트는 `test_manual_data_guards.py`, `test_scheduled_input_gate.py`, `test_state_write_boundary.py`) → K2 유지 |
| `alert_policy.json` | 원시 `860fb038…`. Cowork 병합 뒤 기록 `860FB038…`과 같음 |
| `portfolio_state.json` | `fbb7808c…`. 작업 전후와 본 폴더가 모두 같음 |
| `alert_runtime_state.json` | `5a4e611f…`. 작업 전후와 본 폴더가 모두 같음 |
| 금지 항목 | `apply` 실행 0, 키움 접속 0, 커밋·푸시 0, 줄바꿈 일괄 변환 0 |

## 5. 남는 점

1. **이름과 단언이 어긋난 테스트 3개**는 S7 2차에서 정리합니다. `test_active_policy_generates_only_review_candidate`, `test_inv_06_timing_quantities_unchanged`(2곳)이 해당합니다(이전 보고서 §6-7).
2. **픽스처가 여전히 실제 상태에 기대는 부분이 있습니다.**
   - 보유 수량은 합성값이지만 `timing_plan`(anchor 396·99, SOXL R25 완료), `strategy_version`, 원가 등은 실제 상태 파일에서 읽습니다.
   - 실제 `timing_plan`이 바뀌면 anchor 정렬값도 따라 바뀝니다. 그래서 "Broker=396"처럼 396을 박아 둔 단언은 다시 어긋날 수 있습니다.
   - 완전한 분리(합성 상태 전체)는 이번 범위 밖입니다.
3. **worktree에서는 이 묶음 140건이 실행되지 않습니다**(1-1). 앞으로 Builder·Judge가 worktree에서 대시보드 모듈을 확인하려면 바이트 사본이 필요합니다. 이번 `make_byte_copy.py` 방식이나 원본 폴더 실행이 그 예입니다. 근본 해결 후보는 `.gitattributes`에서 artifact를 `-text`로 지정하는 것이고, 이는 K2/K3 판단이 필요한 별도 작업입니다.
4. `test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan` 1건은 원인 미분석입니다(변경 전후 같음).

## 6. 확인 필요

1. 원본 폴더(본 체크아웃)에서 이 묶음이 통과하는지는 확인하지 않았습니다. 바이트 사본은 artifact가 LF이고 상태가 같다는 점에서 원본 폴더와 같은 조건으로 봅니다. Cowork 재실행 때 확인하면 됩니다.
2. 원본 폴더의 artifact 줄바꿈은 본 폴더 1개 파일(`a8a3…`, 원시 해시 일치)만 확인했습니다. 나머지 12개는 확인하지 않았습니다.
3. 1-3의 클래스별 건수는 `unittest -v` 결과 줄(subtest 실패 포함) 기준입니다. 클래스별 테스트 메서드 수와는 다를 수 있습니다.
