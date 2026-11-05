---
id: postapply-d4-report
title: "postapply-d4 Builder 보고 — 대조 뒤 검사에서 D4 폐지 목록 대조 제거, 신원은 원본 등록부로"
date: 2026-11-05
source: docs/claude/postapply-d4-builder-prompt.md
---

## (a) 바꾼 줄

manage-us-stock-strategy/scripts/reconcile_broker_state.py
- 52~70행: 모듈 상수 추가
  - `CANONICAL_INSTRUMENT_REGISTRY = REPO_ROOT / "workspace/policies/instrument_registry.json"`
  - `D4_RETIRED_ERROR_PREFIXES` (a·b 접두), `D4_RETIRED_ERRORS` (c), `D4_RETIRED_UNHELD_PREFIXES` (d, 보유하지 않은 종목만),
    `POLICY_COPY_IDENTITY_SUFFIXES` (e, 정책 사본 신원 오류 세 종류). 주석 "D4 2026-10-01 원가 손실 한도 폐지".
- 92~99행: `_is_d4_retired_error(error, positive)` — (a)~(d) 판정. (d)는 `X`가 P(양수 보유)에 없을 때만 참.
- 102~116행: `canonical_identity_errors(positive, registry_path)` — 원본 등록부 `instruments[X]`가 dict이고
  `identity_status`가 `"verified"`로 시작하면 통과, 아니면 `X: canonical instrument registry record is missing or unverified`.
  읽기·해석 실패(파일 없음, JSON 오류, `instruments` 없음/객체 아님)는 `canonical instrument registry is unreadable` 한 줄, 예외는 밖으로 던지지 않음.
- 119~145행: `alert_engine_check(alert_policy, *, registry_path=CANONICAL_INSTRUMENT_REGISTRY)`
  - `leveraged_state_integrity_errors(preview, alert_policy, session_date)` 호출은 그대로. 결과에서 (a)~(e)만 빼고 순서 유지, 뒤에 등록부 신원 오류를 더함.
  - P는 evaluate_alerts와 같은 규칙(`finite_number(q) and int(q) > 0`)으로 계산 — 엔진이 정책 사본 신원 오류를 내던 종목 집합과 같은 집합을 등록부로 검사.
  - `policy_positions_mismatch`는 LEVERAGED 경로와 NOT_APPLICABLE 경로 모두 항상 False(필드는 스키마 호환으로 유지).
  - status: 남은 오류가 있으면 FAIL, 없으면 PASS(기존 규칙 그대로). 결과 필드 이름·수 변화 없음.
  - 그 밖의 엔진 오류(전략 버전·스냅샷 검증·신선도·소액 예외 한도·타이밍 기준·보유 종목 수량/평균 단가·폐지 목록 규칙값 형식 오류 등)는 빼지 않음.

manage-us-stock-strategy/tests/test_reconcile_broker_state.py
- 414~416행: 기존 시험 `test_real_alert_engine_check_runs_on_a_patched_copy` 끝 단언 2개 변경 + 주석 1줄 변경.
- 418~488행: 새 시험 `test_alert_check_ignores_retired_cost_loss_list_d4`.

바꾸지 않은 것: kiwoom_broker_shadow.py · evaluate_alerts.py · auto_core_reconcile.py · 스키마 · 로케일 · 정책 · 등록부 · 상태.
줄바꿈: 두 코드 파일 모두 작업 트리 CRLF(색인 i/lf) 그대로, 바꾼 줄만 diff에 나옴.

## (b) 시험

바꾼 기존 단언 2개 (`test_real_alert_engine_check_runs_on_a_patched_copy`)
- `assertTrue(checks["policy_positions_mismatch"])` → `assertFalse(checks["policy_positions_mismatch"])`
- `assertIn("POLICY_POSITIONS_MISMATCH", proposal["warnings"])` → `assertNotIn("POLICY_POSITIONS_MISMATCH", proposal["warnings"])`
- status FAIL 단언은 그대로. 주석: "synthetic tickers are not in the canonical instrument registry".

새 시험 `test_alert_check_ignores_retired_cost_loss_list_d4`
- 실제 `stock-strategy-system/alert_policy.json`을 읽기만 함(시험 끝에 해시 불변 단언). 폐지 목록이 SOXL·MVLL·NBIS이고 범위가 leveraged임을 먼저 단언.
- 기존 fixture(`base_state`, `holding_row`, `account_results`, `make_proposal`)로 preview 보유가 BE·LITE·SOXL(양수, 평균 단가 양수)이 되는 제안을 만들고 그 집합을 단언. 등록부는 임시 폴더 JSON(`registry_path`).
- (가) 오류에 (a)·(b) 접두 문자열, MVLL·NBIS의 수량·평균 단가 4문자열, `holding risk position rules are missing`이 없다.
- (나) 등록부 BE·SOXL = `verified_by_existing_active_policy`, LITE 없음 → `LITE: canonical instrument registry record is missing or unverified` 있음, BE·SOXL 신원 오류 없음, 정책 사본 신원 오류 문자열 없음, status FAIL.
- (다) check 결과와 제안의 `policy_positions_mismatch` False, 경고에 `POLICY_POSITIONS_MISMATCH` 없음.
- (라) 등록부에 LITE도 verified → 등록부 신원 오류 없음. 이때 남는 다른 오류(단언 안 함, 기록만):
  `timing-plan policy version does not match active timing policy` — 합성 `base_state`의 timing_plan 버전이 "TEST"라서 나는 것(이번 변경과 무관, 그대로 둠).
- (마) 보유 중인 SOXL의 평균 단가를 제안 patch에서 빼면 `missing positive verified average cost for SOXL`이 남는다.
- 추가: 등록부 파일이 없으면 `canonical instrument registry is unreadable`이 나오고 status FAIL(조용히 통과하지 않음).
- skip 추가 없음.

## (c) 시험 결과 마지막 3줄

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_reconcile_broker_state*.py"`

```
Ran 57 tests in 0.922s

OK
```

## (d) 운영 영향 예상 (손으로 따라감, 읽기만)

11/05 reconcile.json 원본은 이 worktree 밖(작업 디렉터리 밖 읽기 권한 없음)이라 직접 열지 못했다. 9줄 구성은
docs/claude/post-apply-policy-mismatch-proposal-2026-11-05.md 20~23행 기준으로 따라갔다(원본 대조는 Judge/운영 확인 필요).

| 11/05 오류 | 분류 | 수정 뒤 |
|---|---|---|
| BE·LITE 규칙도 소액 예외도 없음 | (a) | 빠짐 |
| MVLL·NBIS가 보유가 아님 | (b) | 빠짐 |
| MVLL 수량 없음 | (d), 미보유 | 빠짐 |
| MVLL 평균 단가 없음 | (d), 미보유 | 빠짐 |
| NBIS 수량 없음 | (d), 미보유 | 빠짐 |
| NBIS 평균 단가 없음 | (d), 미보유 | 빠짐 |
| BE 신원 미확인(정책 사본) | (e) | 빠짐 → 원본 등록부 BE `verified_by_existing_active_policy` 통과 |
| BE 공식 출처 없음(정책 사본) | (e) | 빠짐 → 위와 같음 |
| LITE 신원 기록 없음(정책 사본) | (e) | 빠짐 → 원본 등록부에 LITE 없음: `LITE: canonical instrument registry record is missing or unverified` 1줄 새로 남 |

SOXL: 원본 등록부 `verified_by_existing_active_policy` → 신원 오류 없음.
예상 결과: 오류 1줄(LITE 등록부 신원)만 남고 POST_APPLY_ALERT_ENGINE_CHECK_FAILED 경고는 계속 붙음(FAIL), POLICY_POSITIONS_MISMATCH 경고는 사라짐.
LITE 줄을 없애려면 원본 등록부에 LITE 신원 기록이 필요(정책 파일 변경 — 이번 범위 밖, 사장 승인 사항).

표지 없음.
