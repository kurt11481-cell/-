---
id: postapply-d4-builder-prompt
title: "대조 뒤 검사에서 폐지된 원가 손실 목록(D4) 대조를 빼고, 종목 신원은 원본 등록부로 보기 — postapply-d4"
date: 2026-11-05
class: "authority(대조 뒤 검사 수정 — 보호 경로 reconcile_broker_state.py). 개발 큐 authority: Builder(Opus) → Judge → 병합은 사장 결정 + -ApproveAuthority"
source: "사장 결정 카드 'A 코드 정리 (추천)'(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9KmPV2aNmo9gsrpx86fTyWZ, 질문 '매일 나오는 코어 경고 2건을 어떻게 정리할까요?', 2026-11-05 13:20:36 KST, 계정=사장). 근거 docs/claude/post-apply-policy-mismatch-proposal-2026-11-05.md"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음 · alert_policy.json·instrument_registry.json 수정 없음"
---

## 목표
매일 06:15 대조(reconcile)에서 경고 2건(POST_APPLY_ALERT_ENGINE_CHECK_FAILED, POLICY_POSITIONS_MISMATCH)과 오류 9줄이 나온다(workspace/outputs/auto-core/2026-11-05/reconcile.json). 원인은 `reconcile_broker_state.alert_engine_check`(73~92행)가 보유를 `alert_policy.json`의 `holding_risk_rules.positions`(SOXL·MVLL·NBIS)와 대조하기 때문이다. 이 목록은 원가 손실 한도 규칙이고, 2026-10-01 사장 결정 D4로 판정 규칙에서 폐지됐다(docs/claude/active-decisions.md G절 D4 행). 그리고 종목 신원을 정책 파일 안의 사본(`decision_harness.instrument_registry`)으로 본다.

`alert_engine_check`만 고쳐서 아래 두 가지를 바꾼다. 나머지 검사는 그대로 둔다.
- 폐지된 목록과의 대조는 오류로 올리지 않는다.
- 종목 신원은 원본 등록부 `workspace/policies/instrument_registry.json`의 `instruments`로 본다.

## 바꿀 파일 (이 3개만)
- manage-us-stock-strategy/scripts/reconcile_broker_state.py
- manage-us-stock-strategy/tests/test_reconcile_broker_state.py
- docs/claude/postapply-d4-report.md (보고)

## 구현 요구 (reconcile_broker_state.py)
1. `alert_engine_check`가 `leveraged_state_integrity_errors(preview, alert_policy, session_date)`를 부르는 방식은 그대로 둔다. 그 결과 오류 목록에서 아래 항목만 빼고 나머지는 순서대로 둔다. 빼는 오류는 모두 그 함수(evaluate_alerts.py 489~545행)가 내는 문자열이다. 빼는 규칙은 모듈 상수로 둔다(이름 예: `D4_RETIRED_ERROR_PREFIXES`, 주석에 "D4 2026-10-01 원가 손실 한도 폐지"). 집합 P는 preview의 양수 보유 종목이다.
   - (a) `positive holdings contain symbols with neither a holding-risk rule nor a de-minimis exception: ` 로 시작하는 오류
   - (b) `holding-risk policy symbols are not positive verified holdings: ` 로 시작하는 오류
   - (c) `holding risk position rules are missing`
   - (d) `missing positive verified holding quantity for X` 와 `missing positive verified average cost for X` 중 **X가 P에 없는 것만**. X가 P에 있으면(예: 보유 중인 SOXL의 평균 단가 없음) 빼지 않는다.
   - (e) 신원 오류 세 종류 `X: official instrument identity record is missing`, `X: held-instrument identity is not verified`, `X: official issuer identity source is missing` — 모두 뺀 뒤 2번 검사로 바꾼다.
2. 신원 검사: 원본 등록부 JSON을 읽는다. 경로는 모듈 상수 `REPO_ROOT / "workspace/policies/instrument_registry.json"`이고, `alert_engine_check`에 키워드 인자 `registry_path`를 두어 시험에서 바꿀 수 있게 한다. 기본값은 이 상수다. P의 각 종목 X에 대해 `instruments[X]`가 dict이고 `identity_status`가 `"verified"`로 시작하는 문자열이면 통과다. 아니면 오류 `f"{X}: canonical instrument registry record is missing or unverified"`를 더한다. 파일을 읽지 못하면 오류 `"canonical instrument registry is unreadable"` 한 줄을 더한다. 예외를 밖으로 던지지 않는다.
3. `policy_positions_mismatch`는 폐지된 목록과의 대조이므로 항상 False로 낸다. 필드 자체는 스키마 호환을 위해 남긴다. NOT_APPLICABLE 경로도 False로 낸다.
4. status는 남은 오류가 있으면 FAIL, 없으면 PASS다(지금 규칙 그대로).
5. `kiwoom_broker_shadow.py`·`evaluate_alerts.py`·`auto_core_reconcile.py`·스키마·로케일은 바꾸지 않는다. 결과 JSON의 필드 이름이나 필드 수를 늘리지 않는다.
6. 줄바꿈은 지금 그대로 지킨다(두 코드 파일 모두 i/lf).

## 시험 (test_reconcile_broker_state.py)
- 기존 `test_real_alert_engine_check_runs_on_a_patched_copy`(404~416행)의 마지막 두 단언(`policy_positions_mismatch` 참, 경고 `POLICY_POSITIONS_MISMATCH` 있음)은 이번 결정으로 뜻이 바뀐다. 그래서 `assertFalse(checks["policy_positions_mismatch"])`, `assertNotIn("POLICY_POSITIONS_MISMATCH", proposal["warnings"])`로 바꾼다. status FAIL 단언은 그대로 둔다. 합성 종목은 원본 등록부에 없어서 신원 오류가 난다. 그 이유를 주석 한 줄로 고친다. 이 시험 밖의 기존 단언은 바꾸지 않는다.
- 새 시험 1개(이름 예: `test_alert_check_ignores_retired_cost_loss_list_d4`). 정책은 실제 `stock-strategy-system/alert_policy.json`을 읽어 쓰되 파일은 고치지 않는다. 등록부는 임시 폴더의 작은 JSON으로 준다(`registry_path`). preview 보유가 BE·LITE·SOXL(양수, 평균 단가 양수)이 되는 상태를 만들고 아래를 단언한다. 기존 fixture·`make_proposal` 방식을 쓰고, 어렵다면 `alert_engine_check(...)`가 돌려준 check 함수를 직접 불러도 된다.
  - (가) errors에 (a)·(b)·MVLL·NBIS의 수량·평균 단가 문자열이 없다.
  - (나) 등록부에 BE·SOXL은 `identity_status: "verified_by_existing_active_policy"`로, LITE는 넣지 않으면 오류에 `LITE: canonical instrument registry record is missing or unverified`가 있고 BE·SOXL 신원 오류는 없다.
  - (다) `policy_positions_mismatch`는 False다.
  - (라) 등록부에 LITE도 verified로 넣으면 (가)~(다)의 신원 오류가 사라진다. 다른 오류가 남으면 그 목록을 보고서에 적는다(단언은 신원 오류 없음만).
  - (마) 보유 중인 SOXL의 평균 단가를 빼면 `missing positive verified average cost for SOXL`이 **남는다**(빼지 않음 확인).
- skip은 넣지 않는다.
- 실행 명령은 이 한 줄만, 글자 그대로 쓴다: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_reconcile_broker_state*.py"`
- 앞에 환경 변수나 옵션을 붙이지 않는다. 전체 스위트는 파이프라인이 한다. git은 status·diff·log만 쓴다. `python -c`·PowerShell·파이프는 쓰지 않는다.

## 지켜야 할 것
1. 위 3개 파일 밖은 손대지 않는다.
2. 폐지 목록 대조와 정책 사본 신원 검사만 바꾼다. 다른 검사(스냅샷 검증·신선도·소액 예외 한도·타이밍 기준·보유 종목의 수량·평균 단가)는 풀지 않는다.
3. 주문·키움·일지·원장·예약과 무관하다. auto_core.py·kiwoomcli·reconcile apply 실행 금지. git commit·push·병합 없음. 비밀(.env*·토큰·계좌번호)을 읽지 않는다. portfolio_state.json을 읽거나 쓰지 않는다.
4. 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/postapply-d4-report.md
- (a) 바꾼 줄(파일:행)
- (b) 새 시험 이름과 단언 (가)~(마), 바꾼 기존 단언 2개
- (c) 시험 결과 마지막 3줄
- (d) 운영 영향 예상: 11/05 reconcile.json의 오류 9줄 중 이 수정 뒤 남을 줄을 손으로 따라가 적는다(읽기만). 예상: LITE 신원 1줄만 남음

수량·금액은 적지 않는다. 주문·권한 표지 문자열도 적지 않고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 허용 파일 3개뿐이다.
2. 빼는 오류가 (a)~(e)뿐이다. (d)는 보유하지 않은 종목만 뺀다(보유 종목의 수량·평균 단가 오류는 남는다).
3. 신원 검사가 원본 등록부를 읽고, 읽지 못하면 오류를 낸다(조용히 통과하지 않음).
4. policy_positions_mismatch가 False여도 status 판정(오류 있으면 FAIL)은 그대로다.
5. kiwoom_broker_shadow·evaluate_alerts·auto_core_reconcile·스키마·결과 필드 목록이 바뀌지 않았다.
6. 새 시험이 실제 상황(BE·LITE·SOXL 대 SOXL·MVLL·NBIS)을 만들고 (가)~(마)를 단언한다(항상 참 단언 아님). 바꾼 기존 단언은 2개뿐이고 skip 추가 없음.
7. 새 실패 0(파이프라인 checks).
8. 보고서 (a)~(d) 있음, 수량·금액·표지 없음.

```dev-run
{"task_id": "postapply-d4", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 120, "builder_timeout_min": 75, "allowed_paths": ["manage-us-stock-strategy/scripts/reconcile_broker_state.py", "manage-us-stock-strategy/tests/test_reconcile_broker_state.py", "docs/claude/postapply-d4-report.md"], "target_tests": ["test_reconcile_broker_state*.py"], "commit_message": "fix(reconcile): stop comparing holdings with the D4-retired cost-loss list and check identity against the canonical registry (postapply-d4)"}
```
